"""WSGI middlewares used in routemaster."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Tuple,
    Callable,
    Iterable,
    Optional,
)

from routemaster.app import App

if TYPE_CHECKING:
    from _typeshed.wsgi import StartResponse, WSGIApplication, WSGIEnvironment


WSGIMiddleware = Callable[[App, 'WSGIApplication'], 'WSGIApplication']

ACTIVE_MIDDLEWARES: List[WSGIMiddleware]
ACTIVE_MIDDLEWARES = []


def middleware(fn: WSGIMiddleware):
    """Decorator: add `fn` to ACTIVE_MIDDLEWARES."""
    ACTIVE_MIDDLEWARES.append(fn)
    return fn


def wrap_application(app: App, wsgi: 'WSGIApplication') -> 'WSGIApplication':
    """Wrap a given WSGI callable in all active middleware."""
    for middleware_instance in reversed(ACTIVE_MIDDLEWARES):
        wsgi = middleware_instance(app, wsgi)
    return wsgi


# Definitions start here


@middleware
def session_middleware(app: App, wsgi: 'WSGIApplication') -> 'WSGIApplication':
    """Manage an ORM session around each request."""
    def inner(
        environ: 'WSGIEnvironment',
        start_response: 'StartResponse',
    ) -> Iterable[bytes]:
        def wrapped_start_response(
            status: str,
            headers: List[Tuple[str, str]],
            exc_info: Optional[Any] = None,
        ) -> Callable[[bytes], Any]:
            if exc_info is not None:  # pragma: no branch
                app.set_rollback()  # pragma: no cover
            return start_response(status, headers, exc_info)

        with app.new_session():
            yield from wsgi(environ, wrapped_start_response)
    return inner


@middleware
def logging_middleware(app: App, wsgi: 'WSGIApplication') -> 'WSGIApplication':
    """Log requests as they come in."""
    def inner(
        environ: 'WSGIEnvironment',
        start_response: 'StartResponse',
    ) -> Iterable[bytes]:

        kwargs: Dict[str, Any] = {}

        def wrapped_start_response(
            status: str,
            headers: List[Tuple[str, str]],
            exc_info: Optional[Any] = None,
        ) -> Callable[[bytes], Any]:
            kwargs['status'] = status.split()[0]
            kwargs['headers'] = headers
            kwargs['exc_info'] = exc_info
            return start_response(status, headers, exc_info)

        app.logger.process_request_started(environ)
        yield from wsgi(environ, wrapped_start_response)
        app.logger.process_request_finished(environ, **kwargs)

    return inner
