"""Core App singleton that holds state for the application."""
from typing import IO, Any, Dict

import yaml

from routemaster.config import Config, load_config


class App:
    """Core application state."""

    config: Config
    raw_config: Dict[str, Any]

    def __init__(self, config_file: IO[str]) -> None:
        """Initialisation of the app state."""
        self.raw_config = yaml.load(config_file)
        self.config = load_config(self.raw_config)
