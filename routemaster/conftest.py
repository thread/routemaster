import os.path

import pytest

import routemaster
from routemaster.app import App
from routemaster.server import server


@pytest.fixture()
def app(config=None, config_file='realistic.yaml'):
    """Create an instance of App with the given config for testing."""

    app = App()

    if config is None:
        with open(os.path.join('test_data', config_file)) as f:
            app.load_config(f)
    else:
        app.config = config

    return app


@pytest.yield_fixture()
def app_client(loop, test_client, *args, **kwargs):
    """Create a test client for the server running under an app config."""
    _app = routemaster.app
    routemaster.app = app(*args, **kwargs)
    print(routemaster.app)
    yield loop.run_until_complete(test_client(server))
    routemaster.app = _app
