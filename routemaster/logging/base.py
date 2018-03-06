"""Base class for logging plugins."""

import contextlib


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

    def __getattr__(self, name):
        """Implement the Python logger API."""
        if name in (
            'debug',
            'info',
            'warning',
            'error',
            'critical',
            'exception',
        ):
            return self._log_handler

        raise AttributeError(name)

    def _log_handler(self, *args, **kwargs):
        pass
