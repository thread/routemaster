"""Global test setup and fixtures."""

import os
import re
import json
import socket
import datetime
import functools
import contextlib
import subprocess
from typing import Any, Dict
from unittest import mock

import pytest
import httpretty
import dateutil.tz
import pkg_resources
from sqlalchemy import create_engine
from werkzeug.test import Client
from sqlalchemy.orm import sessionmaker
from werkzeug.wrappers import BaseResponse

from routemaster import state_machine
from routemaster.db import Label, History, metadata
from routemaster.app import App
from routemaster.utils import dict_merge
from routemaster.config import (
    Gate,
    Action,
    Config,
    Webhook,
    FeedConfig,
    NoNextStates,
    StateMachine,
    DatabaseConfig,
    OnEntryTrigger,
    MetadataTrigger,
    ConstantNextState,
    ContextNextStates,
    LoggingPluginConfig,
    ContextNextStatesOption,
)
from routemaster.server import server
from routemaster.context import Context
from routemaster.logging import BaseLogger, SplitLogger, register_loggers
from routemaster.webhooks import (
    WebhookResult,
    webhook_runner_for_state_machine,
)
from routemaster.middleware import wrap_application
from routemaster.state_machine import LabelRef
from routemaster.exit_conditions import ExitConditionProgram

TEST_DATABASE_CONFIG = DatabaseConfig(
    host=os.environ.get('PG_HOST', 'localhost'),
    port=int(os.environ.get('PG_PORT', 5432)),
    name=os.environ.get('PG_DB', 'routemaster_test'),
    username=os.environ.get('PG_USER', ''),
    password=os.environ.get('PG_PASS', ''),
)

TEST_STATE_MACHINES = {
    'test_machine': StateMachine(
        name='test_machine',
        feeds=[
            FeedConfig(name='tests', url='http://localhost/tests'),
        ],
        webhooks=[
            Webhook(
                match=re.compile('//(.+\\.)?example\\.com'),
                headers={
                    'x-api-key': 'Rahfew7eed1ierae0moa2sho3ieB1et3ohhum0Ei',
                },
            ),
        ],
        states=[
            Gate(
                name='start',
                triggers=[
                    MetadataTrigger(metadata_path='should_progress'),
                    OnEntryTrigger(),
                ],
                next_states=ContextNextStates(
                    path='feeds.tests.should_do_alternate_action',
                    destinations=[
                        ContextNextStatesOption(
                            state='perform_action',
                            value=False,
                        ),
                        ContextNextStatesOption(
                            state='perform_alternate_action',
                            value=True,
                        ),
                    ],
                    default='perform_action',
                ),
                exit_condition=ExitConditionProgram(
                    'metadata.should_progress = true',
                ),
            ),
            Action(
                name='perform_action',
                webhook='http://localhost/hook/<state_machine>/<label>',
                next_states=ConstantNextState(state='end'),
            ),
            Action(
                name='perform_alternate_action',
                webhook='http://localhost/hook',
                next_states=ContextNextStates(
                    path='feeds.tests.should_loop',
                    destinations=[
                        ContextNextStatesOption(
                            state='end',
                            value=False,
                        ),
                        ContextNextStatesOption(
                            state='start',
                            value=True,
                        ),
                    ],
                    default='end',
                ),
            ),
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ],
    ),
    # This state machine is used for exercising race conditions in tests and is
    # purposefully not realistic.
    'test_machine_2': StateMachine(
        name='test_machine_2',
        feeds=[],
        webhooks=[],
        states=[
            Gate(
                name='gate_1',
                triggers=[
                    OnEntryTrigger(),
                    MetadataTrigger(metadata_path='should_progress'),
                ],
                next_states=ConstantNextState('gate_2'),
                exit_condition=ExitConditionProgram(
                    'metadata.should_progress = true',
                ),
            ),
            Gate(
                name='gate_2',
                triggers=[
                    MetadataTrigger(metadata_path='should_progress'),
                ],
                next_states=ConstantNextState('end'),
                exit_condition=ExitConditionProgram(
                    'metadata.should_progress = true',
                ),
            ),
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ],
    ),
    # This state machine is used for testing the possibility of infinite loops.
    'test_infinite_machine': StateMachine(
        name='test_infinite_machine',
        feeds=[],
        webhooks=[],
        states=[
            Gate(
                name='gate_1',
                triggers=[
                    OnEntryTrigger(),
                    MetadataTrigger(metadata_path='should_progress'),
                ],
                next_states=ConstantNextState('gate_2'),
                exit_condition=ExitConditionProgram(
                    'metadata.should_progress = true',
                ),
            ),
            Gate(
                name='gate_2',
                triggers=[OnEntryTrigger()],
                next_states=ConstantNextState('gate_3'),
                exit_condition=ExitConditionProgram('true'),
            ),
            Gate(
                name='gate_3',
                triggers=[OnEntryTrigger()],
                next_states=ConstantNextState('gate_2'),
                exit_condition=ExitConditionProgram('true'),
            ),
        ],
    ),
    'test_machine_timing': StateMachine(
        name='test_machine_timing',
        feeds=[],
        webhooks=[],
        states=[
            Gate(
                name='start',
                triggers=[
                    OnEntryTrigger(),
                ],
                next_states=ConstantNextState('end'),
                exit_condition=ExitConditionProgram(
                    '1d12h has passed since history.entered_state',
                ),
            ),
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ],
    ),
}

TEST_ENGINE = create_engine(TEST_DATABASE_CONFIG.connstr)


class TestApp(App):
    """
    Mocked App subclass which overloads the `db` property.

    This has two implications:

    1. We use a shared engine in all the tests rather than connecting many
       times (a speed improvement),
    2. We can set a flag on access to `.db` so that we needn't bother with
       resetting the database if nothing has actually been changed.
    """
    def __init__(self, config):
        self.config = config
        self.session_used = False
        self.logger = SplitLogger(config, loggers=register_loggers(config))
        self._session = None
        self._needs_rollback = False
        self._current_session = None
        self._sessionmaker = sessionmaker(bind=TEST_ENGINE)
        self._webhook_runners = {
            x: webhook_runner_for_state_machine(y)
            for x, y in self.config.state_machines.items()
        }

    @property
    def session(self):
        """Start if necessary and return a shared session."""
        self.session_used = True
        return super().session


class TestClientResponse(BaseResponse):
    """Test client response format."""

    @property
    def json(self):
        """Util property for json responses."""
        return json.loads(self.data)


@pytest.fixture()
def client(custom_app=None):
    """Create a werkzeug test client."""
    _app = app() if custom_app is None else custom_app
    server.config.app = _app
    _app.logger.init_flask(server)
    return Client(wrap_application(_app, server), TestClientResponse)


@pytest.fixture()
def app(**kwargs):
    """Create an `App` config object for testing."""
    return TestApp(Config(
        state_machines=kwargs.get('state_machines', TEST_STATE_MACHINES),
        database=kwargs.get('database', TEST_DATABASE_CONFIG),
        logging_plugins=kwargs.get('logging_plugins', [
            LoggingPluginConfig(
                dotted_path='routemaster.logging:PythonLogger',
                kwargs={'log_level': 'DEBUG'},
            ),
        ]),
    ))


@pytest.fixture()
def custom_app():
    """Return the app config fixture directly so that we can modify config."""
    return app


@pytest.fixture()
def app_env():
    """
    Create a dict of environment variables.

    Mirrors the testing environment for use in subprocesses.
    """
    return {
        'DB_HOST': TEST_DATABASE_CONFIG.host,
        'DB_PORT': str(TEST_DATABASE_CONFIG.port),
        'DB_NAME': TEST_DATABASE_CONFIG.name,
        'DB_USER': TEST_DATABASE_CONFIG.username,
        'DB_PASS': TEST_DATABASE_CONFIG.password,
    }


@pytest.fixture(autouse=True, scope='session')
def database_creation(request):
    """Wrap test session in creating and destroying all required tables."""
    metadata.drop_all(bind=TEST_ENGINE)
    metadata.create_all(bind=TEST_ENGINE)
    yield


@pytest.yield_fixture(autouse=True)
def database_clear(app):
    """Truncate all tables after each test."""
    yield
    if app.session_used:
        with app.new_session():
            for table in metadata.tables:
                app.session.execute(
                    f'truncate table {table} cascade',
                    {},
                )


@pytest.fixture()
def create_label(app, mock_test_feed):
    """Create a label in the database."""

    def _create(
        name: str,
        state_machine_name: str,
        metadata: Dict[str, Any],
    ) -> LabelRef:
        with mock_test_feed(), app.new_session():
            state_machine.create_label(
                app,
                LabelRef(name, state_machine_name),
                metadata,
            )
            return LabelRef(name, state_machine_name)

    return _create


@pytest.fixture()
def delete_label(app):
    """
    Mark a label in the database as deleted.
    """

    def _delete(name: str, state_machine_name: str) -> None:
        with app.new_session():
            state_machine.delete_label(
                app,
                LabelRef(name, state_machine_name),
            )

    return _delete


@pytest.fixture()
def create_deleted_label(create_label, delete_label):
    """
    Create a label in the database and then delete it.
    """

    def _create_and_delete(name: str, state_machine_name: str) -> LabelRef:
        create_label(name, state_machine_name, {})
        delete_label(name, state_machine_name)
        return LabelRef(name, state_machine_name)

    return _create_and_delete


@pytest.fixture()
def mock_webhook():
    """Mock the test config's webhook call."""
    @contextlib.contextmanager
    def _mock(result=WebhookResult.SUCCESS):
        runner = mock.Mock(return_value=result)
        with mock.patch(
            'routemaster.app.App.get_webhook_runner',
            return_value=runner,
        ):
            yield runner
    return _mock


@pytest.fixture()
def mock_test_feed():
    """Mock out the test feed."""
    @contextlib.contextmanager
    def _mock(data={'should_do_alternate_action': False}):
        httpretty.enable()
        httpretty.register_uri(
            httpretty.GET,
            'http://localhost/tests',
            body=json.dumps(data),
            content_type='application/json',
        )

        try:
            yield
        finally:
            httpretty.disable()
            httpretty.reset()

    return _mock


@pytest.fixture()
def assert_history(app):
    """Assert that the database history matches what is expected."""
    def _assert(entries):
        with app.new_session():
            history_entries = [
                (x.old_state, x.new_state)
                for x in app.session.query(
                    History,
                ).order_by(
                    History.id,
                )
            ]

            assert history_entries == entries
    return _assert


@pytest.fixture()
def set_metadata(app):
    """Directly set the metadata for a label in the database."""
    def _inner(label, update):
        with app.new_session():
            db_label = app.session.query(Label).filter_by(
                name=label.name,
                state_machine=label.state_machine,
            ).first()

            db_label.metadata = dict_merge(db_label.metadata, update)
            db_label.metadata_triggers_processed = True

            return db_label.metadata
    return _inner


@pytest.fixture()
def make_context(app):
    """Factory for Contexts that provides sane defaults for testing."""
    def _inner(**kwargs):
        logger = BaseLogger(app.config)
        state_machine = app.config.state_machines['test_machine']
        state = state_machine.states[0]

        @contextlib.contextmanager
        def feed_logging_context(feed_url):
            with logger.process_feed(state_machine, state, feed_url):
                yield functools.partial(
                    logger.feed_response,
                    state_machine,
                    state,
                    feed_url,
                )

        return Context(
            label=kwargs['label'],
            metadata=kwargs.get('metadata', {}),
            now=kwargs.get('now', datetime.datetime.now(dateutil.tz.tzutc())),
            feeds=kwargs.get('feeds', {}),
            accessed_variables=kwargs.get('accessed_variables', []),
            current_history_entry=kwargs.get('current_history_entry'),
            feed_logging_context=kwargs.get(
                'feed_logging_context',
                feed_logging_context,
            ),
        )
    return _inner


@pytest.fixture()
def version():
    """Return the package version."""
    try:
        return pkg_resources.working_set.by_key['routemaster'].version
    except KeyError:  # pragma: no cover
        return 'development'


@pytest.fixture()
def current_state(app):
    """Get the current state of a label."""
    def _inner(label):
        with app.new_session():
            return app.session.query(
                History.new_state,
            ).filter_by(
                label_name=label.name,
                label_state_machine=label.state_machine,
            ).order_by(
                History.id.desc(),
            ).limit(1).scalar()
    return _inner


@pytest.fixture()
def unused_tcp_port():
    """Returns an unused TCP port, inspired by pytest-asyncio."""
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture()
def routemaster_serve_subprocess(unused_tcp_port):
    """
    Fixture to spawn a routemaster server as a subprocess.

    Yields the process reference, and the port that it can be accessed on.
    """

    @contextlib.contextmanager
    def _inner():
        env = os.environ.copy()
        env.update({
            'DB_HOST': os.environ.get('PG_HOST', 'localhost'),
            'DB_PORT': os.environ.get('PG_PORT', '5432'),
            'DB_NAME': os.environ.get('PG_DB', 'routemaster_test'),
            'DB_USER': os.environ.get('PG_USER', ''),
            'DB_PASS': os.environ.get('PG_PASS', ''),
        })

        try:
            proc = subprocess.Popen(
                [
                    'routemaster',
                    '--config-file=example.yaml',
                    'serve',
                    '--bind',
                    f'127.0.0.1:{unused_tcp_port}',
                ],
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            yield proc, unused_tcp_port
        finally:
            proc.terminate()

    return _inner
