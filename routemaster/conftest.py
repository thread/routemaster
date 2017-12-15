"""Global test setup and fixtures."""

import os
from typing import Any, Dict

import pytest
from sqlalchemy import create_engine

from routemaster.db import labels, metadata
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
                exit_condition=ExitConditionProgram('should_progress = true'),
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
def app_client(test_client):
    """Create a test client for the server running under an app config."""
    def _create_client(app=None):
        if app is None:
            app = app_factory()()
        server.config.app = app
        return test_client(server)
    return _create_client


@pytest.fixture()
def app_factory():
    """Create an app, prefilled with test defaults."""
    def _create(**kwargs):
        return App(Config(
            state_machines=kwargs.get('state_machines', TEST_STATE_MACHINES),
            database=kwargs.get('database', TEST_DATABASE_CONFIG)
        ))
    return _create


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
def create_label(app_factory):
    """Create a label in the database."""
    app = app_factory()

    def _create(name: str, state_machine: str, context: Dict[str, Any]):
        with app.db.begin() as conn:
            conn.execute(labels.insert().values(
                name=name,
                state_machine=state_machine,
                context=context,
            ))

    return _create
