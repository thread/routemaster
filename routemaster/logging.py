"""Logging interface."""
import importlib

from routemaster.config import Config, LoggingPluginConfig


class BaseLogger:
    """Base class for logging plugins."""
    def __init__(self, config, *args, **kwargs):
        self.config = config


class PluginConfigurationException(Exception):
    """Raised to signal an invalid plugin that was loaded."""


def register_loggers(config: Config):
    """
    Iterate through all plugins in the config file and instatiate them.
    """
    return [_import_logger(config, x) for x in config.logging_plugins]


def _import_logger(
    config: Config,
    logger_config: LoggingPluginConfig,
) -> BaseLogger:
    dotted_path = logger_config.dotted_path.split('.')

    module = importlib.import_module('.'.join(dotted_path[:-1]))
    klass = getattr(module, dotted_path[-1])

    if not issubclass(klass, BaseLogger):
        raise PluginConfigurationException(
            f"{klass} must inherit from routemaster.logging.BaseLogger",
        )

    return klass(config, **logger_config.kwargs)
