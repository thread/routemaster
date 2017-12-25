"""WSGI middlewares used in routemaster."""

import logging
from typing import Dict, List, Callable, Iterable

from routemaster.app import App
from routemaster.utils import WSGICallable, StartResponse, WSGIEnvironment

WSGIMiddleware = Callable[[App, WSGICallable], WSGICallable]

ACTIVE_MIDDLEWARES: List[WSGIMiddleware]
ACTIVE_MIDDLEWARES = []

LOGGER = logging.getLogger("routemaster.middleware")


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
            exc_info: None,
        ) -> None:
            if exc_info is not None:
                app.set_rollback()
            start_response(status, headers, exc_info)

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
        LOGGER.info("{method} {path}".format(
            method=environ['REQUEST_METHOD'],
            path=environ['PATH_INFO'],
        ))

        yield from wsgi(environ, start_response)
    return inner