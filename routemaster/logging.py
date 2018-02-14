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

        for log_fn in (
            'debug',
            'info',
            'warning',
            'error',
            'critical',
            'log',
            'exception',
        ):
            setattr(self, log_fn, self._log_handler)

    def _log_handler(self, *args, **kwargs):
        pass

    @contextlib.contextmanager
    def process_cron(self, state_machine, state, fn_name):
        """Wraps the processing of a cron job for logging purposes."""
        yield


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

        for log_fn in (
            'debug',
            'info',
            'warning',
            'error',
            'critical',
            'log',
            'exception',
        ):
            setattr(self, log_fn, getattr(self.logger, log_fn))

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


class LoggerProxy:
    """Proxies logging calls to all loggers in a list."""

    def __init__(self, loggers: List[BaseLogger]) -> None:
        self.loggers = loggers

    def __getattribute__(self, name):
        """Return a proxy function that will dispatch to all loggers."""
        if name == 'loggers':
            return super().__getattribute__(name)

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
    dotted_path = logger_config.dotted_path.split('.')

    module = importlib.import_module('.'.join(dotted_path[:-1]))
    klass = getattr(module, dotted_path[-1])

    if not issubclass(klass, BaseLogger):
        raise PluginConfigurationException(
            f"{klass} must inherit from routemaster.logging.BaseLogger",
        )

    return klass(config, **logger_config.kwargs)
