"""Base class for logging plugins."""

import contextlib
from typing import Any, Dict, Type, Tuple, Callable, Iterator, Optional

import requests
from flask.app import Flask

from routemaster.config import State, Config, StateMachine


class BaseLogger:
    """Base class for logging plugins."""

    def __init__(self, config: Optional[Config], *args, **kwargs) -> None:
        self.config = config

    def init_flask(self, flask_app: Flask) -> None:
        """
        Entrypoint for configuring logging on the flask server.

        Note: this is only called if routemaster is being run as a server, not
        when validating configuration for example.
        """
        pass

    @contextlib.contextmanager
    def process_cron(
        self,
        state_machine: StateMachine,
        state: State,
        fn_name: str,
    ) -> Iterator[None]:
        """Wraps the processing of a cron job for logging purposes."""
        yield

    @contextlib.contextmanager
    def process_webhook(
        self,
        state_machine: StateMachine,
        state: State,
    ) -> Iterator[None]:
        """Wraps the processing of a webhook for logging purposes."""
        yield

    def process_request_started(self, environ: Dict[str, Any]) -> None:
        """Request started."""
        pass

    def process_request_finished(
        self,
        environ: Dict[str, Any],
        *,
        status: int,
        headers: Dict[str, Any],
        exc_info: Optional[Tuple[Type[RuntimeError], RuntimeError, None]],
    ) -> None:
        """Completes the processing of a request."""
        pass

    def webhook_response(
        self,
        state_machine: StateMachine,
        state: State,
        response: requests.Response,
    ) -> None:
        """Logs the receipt of a response from a webhook."""
        pass

    @contextlib.contextmanager
    def process_feed(
        self,
        state_machine: StateMachine,
        state: State,
        feed_url: str,
    ) -> Iterator[None]:
        """Wraps the processing of a feed for logging purposes."""
        yield

    def feed_response(
        self,
        state_machine: StateMachine,
        state: State,
        feed_url: str,
        response: requests.Response,
    ) -> None:
        """Logs the receipt of a response from a feed."""
        pass

    def __getattr__(self, name: str) -> Callable[[str], None]:
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

    def _log_handler(self, *args, **kwargs) -> None:
        pass
