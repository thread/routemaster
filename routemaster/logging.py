"""Logging interface."""
from routemaster.config import Config


class BaseLogger:
    """Base class for logging plugins."""
    pass


def register_loggers(config: Config):
    """
    Iterate through all plugins in the config file and instatiate them.
    """
    pass
