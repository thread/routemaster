"""Core App singleton that holds state for the application."""
from typing import IO, Any, Dict

import yaml

from routemaster.config import Config, load_config


class App(object):
    """Core application state."""

    config: Config
    raw_config: Dict[str, Any]

    def load_config(self, config_file: IO[str]) -> None:
        """Load configuration from a file."""
        self.raw_config = yaml.load(config_file)
        self.config = load_config(self.raw_config)
