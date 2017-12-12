import os.path

import pytest

from routemaster.app import App
from routemaster.server import server


def app(config_file='realistic.yaml'):
    """Create an instance of App with the given config for testing."""

    with open(os.path.join('test_data', config_file)) as f:
        return App(f)


@pytest.fixture()
def app_client(test_client, loop):
    """Create a test client for the server running under an app config."""
    async def _create_client(*args, **kwargs):
        server.config.app = app(*args, **kwargs)
        client = await test_client(server)
        return client
    return _create_client
