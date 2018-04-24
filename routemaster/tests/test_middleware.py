import pytest

from werkzeug.test import run_wsgi_app

from routemaster.db import Label
from routemaster.middleware import session_middleware


def test_session_middleware(app):
    def server(environ, start_response):
        start_response(200, {})

        # There should be an active session. Accessing .session would throw
        # an exception if there wasn't one.
        assert app.session is not None

        return b''

    wrapped_server = session_middleware(app, server)
    run_wsgi_app(wrapped_server, {})


def test_session_middleware_commits_transaction(app):
    def server(environ, start_response):
        start_response(200, {})

        app.session.add(Label(
            name='foo',
            state_machine='test_machine',
            metadata={},
        ))

        return b''

    wrapped_server = session_middleware(app, server)
    run_wsgi_app(wrapped_server, {})

    with app.new_session():
        assert app.session.query(Label).count() == 1


def test_session_middleware_rolls_back_transaction(app):
    def server(environ, start_response):
        start_response(200, {})

        app.session.add(Label(
            name='foo',
            state_machine='test_machine',
            metadata={},
        ))

        raise RuntimeError()

    wrapped_server = session_middleware(app, server)

    with pytest.raises(RuntimeError):
        run_wsgi_app(wrapped_server, {})

    with app.new_session():
        assert app.session.query(Label).count() == 0
