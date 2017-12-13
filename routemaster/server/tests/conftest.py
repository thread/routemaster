import os

import pytest

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


@pytest.fixture()
def app_client(test_client):
    """Create a test client for the server running under an app config."""
    def _create_client(config=TEST_CONFIG):
        server.config.app = App(config)
        return test_client(server)
    return _create_client


@pytest.fixture()
def app_config() -> Config:
    """Create a config, prefilled with test defaults."""
    def _create(**kwargs):
        return Config(
            state_machines=kwargs.get('state_machines', {}),
            database=kwargs.get('database', TEST_DATABASE_CONFIG)
        )
    return _create
