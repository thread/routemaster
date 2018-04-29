"""WSGI middlewares used in routemaster."""

from typing import Any, Dict, List, Callable, Iterable, Optional

from routemaster.app import App
from routemaster.utils import WSGICallable, StartResponse, WSGIEnvironment

WSGIMiddleware = Callable[[App, WSGICallable], WSGICallable]

ACTIVE_MIDDLEWARES: List[WSGIMiddleware]
ACTIVE_MIDDLEWARES = []


def middleware(fn: WSGIMiddleware):
    """Decorator: add `fn` to ACTIVE_MIDDLEWARES."""
    ACTIVE_MIDDLEWARES.append(fn)
    return fn


def wrap_application(app: App, wsgi: WSGICallable) -> WSGICallable:
    """Wrap a given WSGI callable in all active middleware."""
    for middleware_instance in reversed(ACTIVE_MIDDLEWARES):
        wsgi = middleware_instance(app, wsgi)
    return wsgi


# Definitions start here


@middleware
def session_middleware(app: App, wsgi: WSGICallable) -> WSGICallable:
    """Manage an ORM session around each request."""
    def inner(
        environ: WSGIEnvironment,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        def wrapped_start_response(
            status: str,
            headers: Dict[str, str],
            exc_info: Optional[Any] = None,
        ) -> None:
            start_response(status, headers, exc_info)
            if exc_info is not None:  # pragma: no branch
                app.set_rollback()  # pragma: no cover

        with app.new_session():
            yield from wsgi(environ, wrapped_start_response)
    return inner


@middleware
def logging_middleware(app: App, wsgi: WSGICallable) -> WSGICallable:
    """Log requests as they come in."""
    def inner(
        environ: WSGIEnvironment,
        start_response: StartResponse,
    ) -> Iterable[bytes]:

        kwargs: Dict[str, Any] = {}

        def wrapped_start_response(
            status: str,
            headers: Dict[str, str],
            exc_info: Optional[Any] = None,
        ) -> None:
            kwargs['status'] = status.split()[0]
            kwargs['headers'] = headers
            kwargs['exc_info'] = exc_info
            start_response(status, headers, exc_info)

        app.logger.process_request_started(environ)
        yield from wsgi(environ, wrapped_start_response)
        app.logger.process_request_finished(environ, **kwargs)

    return inner
