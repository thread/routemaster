"""Global test setup and fixtures."""

import os
import contextlib
from typing import Any, Dict

import pytest
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from routemaster import state_machine
from routemaster.db import metadata
from routemaster.app import App
from routemaster.config import (
    Gate,
    Config,
    NoNextStates,
    StateMachine,
    ContextTrigger,
    DatabaseConfig,
    ConstantNextState,
)
from routemaster.server import server
from routemaster.middleware import wrap_application
from routemaster.state_machine import Label
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
        states=[
            Gate(
                name='start',
                triggers=[
                    ContextTrigger(context_path='should_progress'),
                ],
                next_states=ConstantNextState(state='end'),
                exit_condition=ExitConditionProgram(
                    'should_progress = true',
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
        self._session = None
        self._needs_rollback = False

    @property
    def db(self):
        """Get the shared DB and set the used flag."""
        raise AssertionError("Cannot access db directly in tests")

    @property
    def session(self):
        """Start if necessary and return a shared session."""
        if self._session is not None:
            return self._session
        self.session_used = True
        self._session = sessionmaker(bind=TEST_ENGINE)()
        return self._session

    @contextlib.contextmanager
    def new_session(self):
        """We make this do nothing in tests except rollbacks."""
        try:
            yield
            if self._needs_rollback:
                self.session.rollback()
        except Exception:
            self.session.rollback()
            raise
        finally:
            self._needs_rollback = False

    def set_rollback(self):
        """Set the rollback flag for leaving `new_session`."""
        self._needs_rollback = True


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
        database=kwargs.get('database', TEST_DATABASE_CONFIG)
    ))


@pytest.yield_fixture(autouse=True, scope='session')
def database_creation():
    """Wrap test session in creating and destroying all required tables."""
    metadata.drop_all(bind=TEST_ENGINE)
    metadata.create_all(bind=TEST_ENGINE)
    yield


@pytest.yield_fixture(autouse=True)
def database_clear(app_config):
    """Truncate all tables after each test."""
    yield
    if app_config.session_used:
        # This does not necessarily imply `databased_used` if everything was
        # done through the ORM session. In that case we can just roll back
        # rather than doing separate truncations.
        app_config.session.rollback()
        app_config.session.close()


@pytest.fixture()
def create_label(app_config):
    """Create a label in the database."""

    def _create(name: str, state_machine_name: str, context: Dict[str, Any]):
        return state_machine.create_label(
            app_config,
            Label(name, state_machine_name),
            context,
        )

    return _create


@pytest.fixture()
def delete_label(app_config):
    """
    Mark a label in the database as deleted.
    """

    def _delete(name: str, state_machine_name: str) -> None:
        state_machine.delete_label(
            app_config,
            Label(name, state_machine_name),
        )

    return _delete


@pytest.fixture()
def create_deleted_label(create_label, delete_label):
    """
    Create a label in the database and then delete it.
    """

    def _create_and_delete(name: str, state_machine_name: str) -> None:
        create_label(name, state_machine_name, {})
        delete_label(name, state_machine_name)

    return _create_and_delete
