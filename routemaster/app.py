"""Core App singleton that holds state for the application."""
import threading

from sqlalchemy.engine import Engine

from routemaster.db import initialise_db
from routemaster.config import Config
from routemaster.logging import BaseLogger, SplitLogger, register_loggers


class App(threading.local):
    """Core application state."""

    db: Engine
    config: Config
    logger: BaseLogger

    def __init__(
        self,
        config: Config,
    ) -> None:
        """Initialisation of the app state."""
        self.config = config
        self.db = initialise_db(self.config.database)

        self.logger = SplitLogger(config, loggers=register_loggers(config))
