"""Global test setup and fixtures."""

import os
import re
import json
import datetime
import contextlib
from typing import Any, Dict
from unittest import mock

import pytest
import httpretty
import dateutil.tz
import pkg_resources
from sqlalchemy import and_, select, create_engine

from routemaster import state_machine
from routemaster.db import labels, history, metadata
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
    ContextNextStatesOption,
)
from routemaster.server import server
from routemaster.context import Context
from routemaster.logging import BaseLogger
from routemaster.webhooks import WebhookResult
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
        self.database_used = False
        self.logger = mock.MagicMock()

    @property
    def db(self):
        """Get the shared DB and set the used flag."""
        self.database_used = True
        return TEST_ENGINE


@pytest.fixture()
def app(**kwargs):
    """Create the Flask app for testing."""
    server.config.app = app_config(**kwargs)
    return server


@pytest.fixture()
def app_config(**kwargs):
    """Create an `App` config object for testing."""
    return TestApp(Config(
        state_machines=kwargs.get('state_machines', TEST_STATE_MACHINES),
        database=kwargs.get('database', TEST_DATABASE_CONFIG),
        logging_plugins=kwargs.get('logging_plugins', []),
    ))


@pytest.fixture()
def custom_app_config():
    """Return the app config fixture directly so that we can modify config."""
    return app_config


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
    metadata.create_all(bind=TEST_ENGINE)
    request.addfinalizer(lambda: metadata.drop_all(bind=TEST_ENGINE))


@pytest.yield_fixture(autouse=True)
def database_clear(app_config):
    """Truncate all tables after each test."""
    yield
    if app_config.database_used:
        with app_config.db.begin() as conn:
            for table in metadata.tables:
                conn.execute(f'truncate table {table} cascade')


@pytest.fixture()
def create_label(app_config, mock_test_feed):
    """Create a label in the database."""

    def _create(
        name: str,
        state_machine_name: str,
        metadata: Dict[str, Any],
    ) -> LabelRef:
        with mock_test_feed():
            state_machine.create_label(
                app_config,
                LabelRef(name, state_machine_name),
                metadata,
            )
            return LabelRef(name, state_machine_name)

    return _create


@pytest.fixture()
def delete_label(app_config):
    """
    Mark a label in the database as deleted.
    """

    def _delete(name: str, state_machine_name: str) -> None:
        state_machine.delete_label(
            app_config,
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
            'routemaster.webhooks.RequestsWebhookRunner',
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
def assert_history(app_config):
    """Assert that the database history matches what is expected."""
    def _assert(entries):
        with app_config.db.begin() as conn:
            history_entries = [
                tuple(x)
                for x in conn.execute(
                    select((
                        history.c.old_state,
                        history.c.new_state,
                    )).order_by(history.c.id.asc()),
                )
            ]

            assert history_entries == entries
    return _assert


@pytest.fixture()
def set_metadata(app_config):
    """Directly set the metadata for a label in the database."""
    def _inner(label, update):
        with app_config.db.begin() as conn:
            filter_ = and_(
                labels.c.name == label.name,
                labels.c.state_machine == label.state_machine,
            )

            existing_metadata = conn.scalar(
                select([labels.c.metadata]).where(filter_),
            )

            new_metadata = dict_merge(existing_metadata, update)

            conn.execute(labels.update().where(filter_).values(
                metadata=new_metadata,
                metadata_triggers_processed=True,
            ))

            return new_metadata
    return _inner


@pytest.fixture()
def make_context(app_config):
    """Factory for Contexts that provides sane defaults for testing."""
    def _inner(**kwargs):
        logger = BaseLogger(app_config.config)
        state_machine = app_config.config.state_machines['test_machine']
        state = state_machine.states[0]

        @contextlib.contextmanager
        def feed_logging_context(feed_url):
            with logger.process_feed(state_machine, state, feed_url):
                yield logger.feed_response

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
    except KeyError:
        return 'development'
