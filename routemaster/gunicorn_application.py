"""Top-level gunicorn application for `routemaster serve`."""

from typing import TYPE_CHECKING, Callable

import gunicorn.app.base

if TYPE_CHECKING:
    from _typeshed.wsgi import WSGIApplication


class GunicornWSGIApplication(gunicorn.app.base.BaseApplication):
    """gunicorn application for routemaster."""

    def __init__(
        self,
        app: 'WSGIApplication',
        *,
        bind: str,
        debug: bool,
        workers: int,
        post_fork: Callable[[], None],
    ) -> None:
        self.application = app
        self.bind = bind
        self.debug = debug
        self.workers = workers
        self.post_fork = post_fork
        super().__init__()

    def load_config(self) -> None:
        """
        Load gunicorn configuration settings.

        Rather than grab these from a file we instead just set them to their
        known values inline.
        """
        self.cfg.set('bind', self.bind)
        self.cfg.set('workers', self.workers)
        self.cfg.set('post_fork', lambda server, workers: self.post_fork())

        if self.debug:
            self.cfg.set('reload', True)
            self.cfg.set('accesslog', '-')

    def load(self) -> 'WSGIApplication':
        """
        Load gunicorn WSGI callable.

        Luckily little loading is needed since this is available inline.
        """
        if self.debug:
            # Inline import so we don't depend on this in production.
            import werkzeug.debug
            return werkzeug.debug.DebuggedApplication(
                self.application,
                evalex=False,
            )
        return self.application
