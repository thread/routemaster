from unittest import mock

import pytest
import werkzeug.test
import werkzeug.testapp

from routemaster.gunicorn_application import GunicornWSGIApplication


@pytest.mark.parametrize('debug', (False, True))
def test_gunicorn_application_can_be_constructed(debug):
    application = GunicornWSGIApplication(
        werkzeug.testapp.test_app,
        bind='[::1]:0',
        debug=debug,
        workers=1,
        post_fork=mock.Mock(),
    )

    application.load_config()
    loaded_wsgi_callable = application.load()

    client = werkzeug.test.Client(
        loaded_wsgi_callable,
        werkzeug.Response,
    )
    response = client.get('/')
    assert response.status_code == 200
    assert response.data.startswith(b'<!DOCTYPE')
