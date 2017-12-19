"""Global test setup and fixtures."""

import os
from typing import Any, Dict

import pytest
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
                    'context.should_progress = true',
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


@pytest.fixture()
def app(**kwargs):
    """Create the Flask app for testing."""
    server.config.app = app_config(**kwargs)
    return server


@pytest.fixture()
def app_config(**kwargs):
    """Create an `App` config object for testing."""
    return App(Config(
        state_machines=kwargs.get('state_machines', TEST_STATE_MACHINES),
        database=kwargs.get('database', TEST_DATABASE_CONFIG)
    ))


@pytest.yield_fixture(autouse=True, scope='session')
def database_creation():
    """Wrap test session in creating and destroying all required tables."""
    metadata.create_all(bind=TEST_ENGINE)
    yield
    metadata.drop_all(bind=TEST_ENGINE)


@pytest.yield_fixture(autouse=True)
def database_clear():
    """Truncate all tables after each test."""
    yield
    with TEST_ENGINE.begin() as conn:
        for table in metadata.tables:
            conn.execute(f'truncate table {table} cascade')


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
def create_deleted_label(client, app_config, create_label):
    """
    Create a label in the database and then delete it.
    """

    def _create_and_delete(name: str, state_machine_name: str) -> None:
        create_label(name, state_machine_name, {})
        state_machine.delete_label(
            app_config,
            Label(name, state_machine_name),
        )

    return _create_and_delete
