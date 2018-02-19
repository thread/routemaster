"""Logger for multiple backends."""

import functools
import contextlib
from typing import List

from routemaster.logging.base import BaseLogger


class SplitLogger(BaseLogger):
    """Proxies logging calls to all loggers in a list."""

    def __init__(self, *args, loggers: List[BaseLogger]) -> None:
        super().__init__(*args)

        self.loggers = loggers

        for fn in (
            'init_flask',

            'debug',
            'info',
            'warning',
            'error',
            'critical',
            'exception',

            'webhook_response',
            'feed_response',
        ):
            setattr(self, fn, functools.partial(self._log_all, fn))

        for fn in (
            'process_cron',
            'process_webhook',
            'process_feed',
        ):
            setattr(self, fn, functools.partial(self._log_all_ctx, fn))

    def _log_all(self, name, *args, **kwargs):
        for logger in self.loggers:
            getattr(logger, name)(*args, **kwargs)

    @contextlib.contextmanager
    def _log_all_ctx(self, name, *args, **kwargs):
        with contextlib.ExitStack() as stack:
            for logger in self.loggers:
                logger_ctx = getattr(logger, name)
                stack.enter_context(logger_ctx(*args, **kwargs))
            yield
