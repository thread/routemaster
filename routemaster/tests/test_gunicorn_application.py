import pytest
import werkzeug.test
import werkzeug.testapp
import werkzeug.wrappers

from routemaster.gunicorn_application import GunicornWSGIApplication


@pytest.mark.parametrize('debug', (False, True))
def test_gunicorn_application_can_be_constructed(debug):
    application = GunicornWSGIApplication(
        werkzeug.testapp.test_app,
        bind='[::1]:0',
        debug=debug,
        workers=1,
    )

    application.load_config()
    loaded_wsgi_callable = application.load()

    client = werkzeug.test.Client(
        loaded_wsgi_callable,
        werkzeug.wrappers.BaseResponse,
    )
    response = client.get('/')
    assert response.status_code == 200
    assert response.data.startswith(b'<!DOCTYPE')
