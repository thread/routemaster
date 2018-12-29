"""Core App singleton that holds state for the application."""
import threading
import contextlib
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

from routemaster.db import initialise_db
from routemaster.config import Config, StateMachine
from routemaster.logging import BaseLogger, SplitLogger, register_loggers
from routemaster.webhooks import (
    WebhookRunner,
    webhook_runner_for_state_machine,
)


def _only_python_logger(logger_configs: Iterable):
    return [x for x in logger_configs if 'PythonLogger' in x.dotted_path]


class App(threading.local):
    """Core application state."""

    _db: Engine
    config: Config
    logger: BaseLogger
    _current_session: Optional[Session]
    _webhook_runners: Dict[str, WebhookRunner]
    use_local_urls: bool
    only_python_logging: bool

    def __init__(
        self,
        config: Config,
        use_local_urls: bool=False,
        only_python_logging: bool=False,
    ) -> None:
        """Initialisation of the app state."""
        self.config = config
        self.use_local_urls = use_local_urls
        self.only_python_logging = only_python_logging
        self.initialise()

    def initialise(self):
        """
        Initialise this instance of the app.

        This may be used to re-initialise after forking in a multiprocessing
        environment.
        """
        self._db = initialise_db(self.config.database)
        logging_plugins = (
            _only_python_logger(self.config.logging_plugins)
            if self.only_python_logging
            else self.config.logging_plugins
        )
        self.logger = SplitLogger(
            self.config,
            loggers=register_loggers(self.config, logging_plugins),
        )
        self._sessionmaker = sessionmaker(self._db)
        self._current_session = None
        self._needs_rollback = False

        # Webhook runners may choose to persist a session, so we instantiate
        # up-front to ensure we re-use state.
        self._webhook_runners = {
            x: webhook_runner_for_state_machine(y, self.use_local_urls)
            for x, y in self.config.state_machines.items()
        }

    @property
    def session(self) -> Session:
        """The current ORM session."""
        if self._current_session is None:
            raise RuntimeError(
                "There is no current session; you can only access `.session` "
                "within a `with app.new_session():` block.",
            )

        return self._current_session

    def set_rollback(self):
        """Mark the current session as needing rollback."""
        if self._current_session is None:
            raise RuntimeError(
                "There is no current session; you can only access `.session` "
                "within a `with app.new_session():` block.",
            )

        self._needs_rollback = True

    @contextlib.contextmanager
    def new_session(self):
        """Run a single session in this scope."""
        if self._current_session is not None:
            raise RuntimeError("There is already a session running.")

        self._current_session = self._sessionmaker()
        try:
            yield
            if self._needs_rollback:
                self._current_session.rollback()
            else:
                self._current_session.commit()

        except:  # noqa: B901, E722 - Unconditional re-raise
            self._current_session.rollback()
            raise

        finally:
            self._current_session.close()
            self._current_session = None
            self._needs_rollback = False

    def get_webhook_runner(self, state_machine: StateMachine) -> WebhookRunner:
        """Get the webhook runner for a state machine."""
        return self._webhook_runners[state_machine.name]
