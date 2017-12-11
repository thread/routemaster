"""Core App singleton that holds state for the application."""

from typing import IO, Optional

import yaml

from routemaster.config import Config, load_config


class App(object):
    """Core application state."""

    config: Optional[Config]
    raw_config: Optional[str]

    def load_config(self, config_file: IO[str]) -> None:
        """Load configuration from a file."""
        self.raw_config = config_file.read()
        self.config = load_config(yaml.load(self.raw_config))
