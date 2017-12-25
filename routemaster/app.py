"""Core App singleton that holds state for the application."""
import threading
import contextlib
from typing import Optional

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine

from routemaster.db import initialise_db
from routemaster.config import Config


class App(threading.local):
    """Core application state."""

    db: Engine
    config: Config
    _current_session: Optional[Session]

    def __init__(self, config: Config) -> None:
        """Initialisation of the app state."""
        self.config = config
        self.db = initialise_db(self.config.database)
        self._sessionmaker = sessionmaker(self.db)
        self._current_session = None
        self._needs_rollback = False

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
        except BaseException:
            self._current_session.rollback()
            raise
        finally:
            self._current_session.close()
            self._current_session = None
            self._needs_rollback = False
