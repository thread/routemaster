"""Plugin loading and configuration."""
import importlib

from routemaster.config import Config, LoggingPluginConfig
from routemaster.logging.base import BaseLogger


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
    dotted_path = logger_config.dotted_path

    try:
        module_path, klass_name = dotted_path.rsplit(':', 2)
    except ValueError:
        raise PluginConfigurationException(
            f"{dotted_path} must be in the form <module-path>:<class-name>",
        )

    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise PluginConfigurationException(
            f"{module_path} does not exist on the PYTHONPATH",
        )

    try:
        klass = getattr(module, klass_name)
    except AttributeError:
        raise PluginConfigurationException(
            f"{klass_name} does not exist in module {module_path}",
        )

    if not callable(klass):
        raise PluginConfigurationException(
            f"{dotted_path} must be callable",
        )

    try:
        logger = klass(config, **logger_config.kwargs)
    except TypeError:
        raise PluginConfigurationException(
            f"Could not instantiate logger, {klass_name} must take a config "
            f"argument and any kwargs specified in the plugin configuration.",
        )

    if not isinstance(logger, BaseLogger):
        raise PluginConfigurationException(
            f"{dotted_path} must inherit from routemaster.logging.BaseLogger",
        )

    return logger
