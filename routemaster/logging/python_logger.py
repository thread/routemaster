"""Routemaster logging interface for Python's logging library."""

import time
import logging
import contextlib

from routemaster.logging.base import BaseLogger


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
        self.logger.info(f"Started logger with level {log_level}")

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

    def process_request_finished(
        self,
        environ,
        *,
        status,
        headers,
        exc_info,
    ):
        """Process a web request and log some basic info about it."""
        self.info("{method} {path} {status}".format(
            method=environ.get('REQUEST_METHOD'),
            path=environ.get('PATH_INFO'),
            status=status,
        ))

    def __getattr__(self, name):
        """Fall back to the logger API."""
        return getattr(self.logger, name)
