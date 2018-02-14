"""Core App singleton that holds state for the application."""
import threading

from sqlalchemy.engine import Engine

from routemaster.db import initialise_db
from routemaster.config import Config
from routemaster.logging import LoggerProxy, register_loggers


class App(threading.local):
    """Core application state."""

    db: Engine
    config: Config
    logger: LoggerProxy

    def __init__(
        self,
        config: Config,
        log_level: str = 'INFO',
    ) -> None:
        """Initialisation of the app state."""
        self.config = config
        self.db = initialise_db(self.config.database)
        self.log_level = log_level

        self.logger = LoggerProxy(register_loggers(config))
