"""Core App singleton that holds state for the application."""
import logging

from sqlalchemy.engine import Engine

from routemaster.db import initialise_db
from routemaster.config import Config


class App:
    """Core application state."""

    db: Engine
    config: Config

    def __init__(self, config: Config, log_level: str = logging.INFO) -> None:
        """Initialisation of the app state."""
        self.config = config
        self.db = initialise_db(self.config.database)
        self.log_level = log_level
