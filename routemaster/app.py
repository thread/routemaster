"""Core App singleton that holds state for the application."""

from typing import IO

import yaml

from routemaster.config import Config, load_config


class App(object):
    """Core application state."""

    config: Config
    raw_config: str

    def load_config(self, config_file: IO[str]) -> None:
        """Load configuration from a file."""
        self.raw_config = yaml.load(config_file.read())
        self.config = load_config(self.raw_config)
