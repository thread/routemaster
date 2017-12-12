import pytest

from routemaster.app import App
from routemaster.config import Config, DatabaseConfig
from routemaster.server import server

TEST_CONFIG = Config(state_machines=[], database=DatabaseConfig(
    host='localhost',
    port=5432,
    name='routemaster',
    username='',
    password='',
))


@pytest.fixture()
def app_client(test_client, loop):
    """Create a test client for the server running under an app config."""
    async def _create_client(config=TEST_CONFIG):
        server.config.app = App(config)
        client = await test_client(server)
        return client
    return _create_client
