"""Logging interface."""
import time
import logging
import importlib
import contextlib
from typing import List

from routemaster.config import Config, LoggingPluginConfig


class BaseLogger:
    """Base class for logging plugins."""

    def __init__(self, config, *args, **kwargs) -> None:
        self.config = config

    def init_flask(self, flask_app):
        """
        Entrypoint for configuring logging on the flask server.

        Note: this is only called if routemaster is being run as a server, not
        when validating configuration for example.
        """
        pass

    @contextlib.contextmanager
    def process_cron(self, state_machine, state, fn_name):
        """Wraps the processing of a cron job for logging purposes."""
        yield

    @contextlib.contextmanager
    def process_webhook(self, state_machine, state):
        """Wraps the processing of a webhook for logging purposes."""
        yield

    def webhook_response(self, response):
        """Logs the receipt of a response from a webhook."""
        pass

    @contextlib.contextmanager
    def process_feed(self, state_machine, state, feed_url):
        """Wraps the processing of a feed for logging purposes."""
        yield

    def feed_response(self, response):
        """Logs the receipt of a response from a feed."""
        pass

    def debug(self, *args, **kwargs):
        """Mirror Python logging API for `debug`."""
        pass

    def info(self, *args, **kwargs):
        """Mirror Python logging API for `info`."""
        pass

    def warning(self, *args, **kwargs):
        """Mirror Python logging API for `warning`."""
        pass

    def error(self, *args, **kwargs):
        """Mirror Python logging API for `error`."""
        pass

    def critical(self, *args, **kwargs):
        """Mirror Python logging API for `critical`."""
        pass

    def log(self, *args, **kwargs):
        """Mirror Python logging API for `log`."""
        pass

    def exception(self, *args, **kwargs):
        """Mirror Python logging API for `exception`."""
        pass


class PythonLogger(BaseLogger):
    """Routemaster logging interface for Python's logging library."""

    def __init__(self, *args, log_level: str) -> None:
        super().__init__(*args)

        logging.basicConfig(
            format=(
                "[%(asctime)s] [%(process)d] [%(levelname)s] "
                "[%(name)s] %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S %z",
            level=getattr(logging, log_level),
        )
        self.logger = logging.getLogger('routemaster')

    @contextlib.contextmanager
    def process_cron(self, state_machine, state, fn_name):
        """Process a cron job, logging information to the Python logger."""
        self.logger.info(
            f"Started cron {fn_name} for state {state.name} in "
            f"{state_machine.name}",
        )
        try:
            time_start = time.time()
            yield
            duration = time.time() - time_start
        except Exception:
            self.logger.exception(f"Error while processing cron {fn_name}")
            raise

        self.logger.info(
            f"Completed cron {fn_name} for state {state.name} "
            f"in {state_machine.name} in {duration:.2f} seconds",
        )

    def debug(self, *args, **kwargs):
        """Mirror Python logging API for `debug`."""
        self.logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        """Mirror Python logging API for `info`."""
        self.logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        """Mirror Python logging API for `warning`."""
        self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        """Mirror Python logging API for `error`."""
        self.logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs):
        """Mirror Python logging API for `critical`."""
        self.logger.critical(*args, **kwargs)

    def log(self, *args, **kwargs):
        """Mirror Python logging API for `log`."""
        self.logger.log(*args, **kwargs)

    def exception(self, *args, **kwargs):
        """Mirror Python logging API for `exception`."""
        self.logger.exception(*args, **kwargs)


class LoggerProxy(BaseLogger):
    """Proxies logging calls to all loggers in a list."""

    def __init__(self, loggers: List[BaseLogger]) -> None:
        self.loggers = loggers

    def __getattr__(self, name):
        """Return a proxy function that will dispatch to all loggers."""
        def log_all(*args, **kwargs):
            for logger in self.loggers:
                getattr(logger, name)(*args, **kwargs)

        @contextlib.contextmanager
        def log_all_ctx(*args, **kwargs):
            with contextlib.ExitStack() as stack:
                for logger in self.loggers:
                    logger_ctx = getattr(logger, name)
                    stack.enter_context(logger_ctx(*args, **kwargs))
                    yield

        if isinstance(
            getattr(BaseLogger, name),
            contextlib.AbstractContextManager,
        ):
            return log_all_ctx
        return log_all


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
