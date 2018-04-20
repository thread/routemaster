import pytest

from werkzeug.test import run_wsgi_app

from routemaster.db import Label
from routemaster.middleware import session_middleware


def test_session_middleware(app_config):
    def server(environ, start_response):
        start_response(200, {})

        # There should be an active session. Accessing .session would throw
        # an exception if there wasn't one.
        assert app_config.session is not None

        return b''

    wrapped_server = session_middleware(app_config, server)
    run_wsgi_app(wrapped_server, {})


def test_session_middleware_commits_transaction(app_config):
    def server(environ, start_response):
        start_response(200, {})

        app_config.session.add(Label(
            name='foo',
            state_machine='test_machine',
            metadata={},
        ))
        app_config.session.flush()

        return b''

    wrapped_server = session_middleware(app_config, server)
    run_wsgi_app(wrapped_server, {})

    with app_config.new_session():
        assert app_config.session.query(Label).count() == 1


def test_session_middleware_rolls_back_transaction(app_config):
    def server(environ, start_response):
        start_response(200, {})

        app_config.session.add(Label(
            name='foo',
            state_machine='test_machine',
            metadata={},
        ))
        app_config.session.flush()

        raise RuntimeError()

    wrapped_server = session_middleware(app_config, server)

    with pytest.raises(RuntimeError):
        run_wsgi_app(wrapped_server, {})

    with app_config.new_session():
        assert app_config.session.query(Label).count() == 0
