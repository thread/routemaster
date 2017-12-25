### DEVELOPMENT INTERACTIVE SCRIPT ###

# Use with `python -i dev.py` for a useful interactive shell.

from routemaster.app import App
from routemaster.db import *
from routemaster.config import load_config

import yaml

with open('example.yaml', 'r') as f:
    config = load_config(yaml.load(f))
del f

class InteractiveApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = self._sessionmaker()

    @property
    def session(self):
        return self._session

app = InteractiveApp(config)
del InteractiveApp
