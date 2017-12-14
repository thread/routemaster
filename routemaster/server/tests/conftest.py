import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from routemaster.db import metadata
from routemaster.app import App
from routemaster.config import Config, DatabaseConfig
from routemaster.server import server

TEST_DATABASE_CONFIG = DatabaseConfig(
    host=os.environ.get('PG_HOST', 'localhost'),
    port=os.environ.get('PG_PORT', 5432),
    name=os.environ.get('PG_DB', 'routemaster_test'),
    username=os.environ.get('PG_USER', ''),
    password=os.environ.get('PG_PASS', ''),
)
TEST_CONFIG = Config(state_machines={}, database=TEST_DATABASE_CONFIG)
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
def app_factory() -> Config:
    """Create an app, prefilled with test defaults."""
    def _create(**kwargs):
        return App(Config(
            state_machines=kwargs.get('state_machines', {}),
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
