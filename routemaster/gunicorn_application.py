"""Top-level gunicorn application for `routemaster serve`."""

from typing import Any, Dict, Callable, Iterable

import werkzeug.debug
import gunicorn.app.base

StartResponse = Callable[
    [
        str,
        Dict[str, str],
        Any,
    ],
    None,
]

WSGICallable = Callable[
    [
        Dict[str, Any],
        StartResponse,
    ],
    Iterable[bytes],
]


class GunicornWSGIApplication(gunicorn.app.base.BaseApplication):
    """gunicorn application for routemaster."""

    def __init__(
        self,
        app: WSGICallable,
        *,
        bind: str,
        debug: bool,
    ) -> None:
        self.application = app
        self.bind = bind
        self.debug = debug
        super().__init__()

    def load_config(self) -> None:
        """
        Load gunicorn configuration settings.

        Rather than grab these from a file we instead just set them to their
        known values inline.
        """
        self.cfg.set('bind', self.bind)
        self.cfg.set('workers', 1)

        if self.debug:
            self.cfg.set('reload', True)
            self.cfg.set('accesslog', '-')

    def load(self) -> WSGICallable:
        """
        Load gunicorn WSGI callable.

        Luckily little loading is needed since this is available inline.
        """
        if self.debug:
            return werkzeug.debug.DebuggedApplication(
                self.application,
                evalex=False,
            )
        return self.application
