"""
Development interactive script.

Use with `python -i dev.py` for a useful interactive shell.
"""

from ruamel import yaml

from routemaster.db import *  # noqa: F403, F401
from routemaster.app import App
from routemaster.config import load_config


def app_from_config(config_path):
    """
    Create an `App` instance with a session from a given config path.

    By default, will use the example.yaml file.
    """
    with open(config_path, 'r') as f:
        config = load_config(yaml.load(f))

    class InteractiveApp(App):
        """
        App for use in interactive shell only.

        Provides a global database session.
        """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._session = self._sessionmaker()

        @property
        def session(self):
            """Return the database session."""
            return self._session

    return InteractiveApp(config)


app = app_from_config('example.yaml')
