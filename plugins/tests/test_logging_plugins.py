import os
import pathlib
from typing import Any, Dict, Type, Tuple, Iterable

import pytest
import requests
from flask import Flask
from routemaster_sentry import SentryLogger
from routemaster_statsd import StatsDLogger
from prometheus_client.core import Sample
from routemaster_prometheus import PrometheusLogger
from prometheus_client.parser import text_string_to_metric_families

from routemaster.logging import BaseLogger, SplitLogger

SENTRY_KWARGS = {
    'dsn': 'https://xxxxxxx:xxxxxxx@sentry.io/xxxxxxx',
    'enabled': False,
}
PROMETHEUS_KWARGS = {
    'path': '/metrics',
}
STATSD_KWARGS = {
    'tags': {
        'env': 'testing',
    },
}

TEST_CASES: Iterable[Tuple[Type[BaseLogger], Dict[str, Any]]] = [
    (SentryLogger, SENTRY_KWARGS),
    (PrometheusLogger, PROMETHEUS_KWARGS),
    (StatsDLogger, STATSD_KWARGS),
    (SplitLogger, {'loggers': [
        SentryLogger(None, **SENTRY_KWARGS),
        PrometheusLogger(None, **PROMETHEUS_KWARGS),
    ]}),
]


@pytest.mark.parametrize('klass, kwargs', TEST_CASES)
def test_logger(app, klass, kwargs):
    logger = klass(app.config, **kwargs)
    state_machine = app.config.state_machines['test_machine']
    state = state_machine.states[0]
    feed_url = 'https://localhost'

    server = Flask('test_server')

    @server.route('/')
    def root():
        return 'Ok', 200

    logger.init_flask(server)

    with logger.process_cron(state_machine, state, 'test_cron'):
        pass

    with pytest.raises(RuntimeError):
        with logger.process_cron(state_machine, state, 'test_cron'):
            raise RuntimeError("Error must propagate")

    with logger.process_feed(state_machine, state, feed_url):
        pass

    with pytest.raises(RuntimeError):
        with logger.process_feed(state_machine, state, feed_url):
            raise RuntimeError("Error must propagate")

    with logger.process_webhook(state_machine, state):
        pass

    with pytest.raises(RuntimeError):
        with logger.process_webhook(state_machine, state):
            raise RuntimeError("Error must propagate")

    # Test valid request
    wsgi_environ = {
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/',
    }
    logger.process_request_started(wsgi_environ)
    logger.process_request_finished(
        wsgi_environ,
        status=200,
        headers={},
        exc_info=None,
    )

    # Test failed request
    wsgi_environ_failed = {
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/',
    }
    logger.process_request_started(wsgi_environ_failed)
    logger.process_request_finished(
        wsgi_environ_failed,
        status=200,
        headers={},
        exc_info=(RuntimeError, RuntimeError('Test exception'), None),
    )

    # Test with invalid path
    wsgi_environ_invalid_path = {
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/non-existent',
    }
    logger.process_request_started(wsgi_environ_invalid_path)
    logger.process_request_finished(
        wsgi_environ_invalid_path,
        status=404,
        headers={},
        exc_info=None,
    )

    logger.debug("test")
    logger.info("test")
    logger.warning("test")
    logger.error("test")
    logger.critical("test")

    try:
        raise ValueError("Test Exception")
    except ValueError:
        logger.exception("test")

    with pytest.raises(AttributeError):
        logger.non_existent_logging_fn("test")

    response = requests.Response()
    logger.webhook_response(state_machine, state, response)
    logger.feed_response(state_machine, state, feed_url, response)


def test_prometheus_logger_wipes_directory_on_startup(app):
    tmp = pathlib.Path(os.environ['PROMETHEUS_MULTIPROC_DIR'])
    tmp.mkdir(parents=True, exist_ok=True)

    filepath = tmp / 'foo.txt'
    dirpath = tmp / 'subdir'

    dirpath.mkdir(parents=True, exist_ok=True)
    with filepath.open('w') as f:
        f.write('Hello, world')

    PrometheusLogger(app.config)

    assert not filepath.exists()
    assert not dirpath.exists()


def test_prometheus_logger_metrics(routemaster_serve_subprocess):
    with routemaster_serve_subprocess(
        wait_for_output=b'Booting worker',
    ) as (proc, port):
        # Populate metrics with a request
        requests.get(f'http://127.0.0.1:{port}/')

        metrics_response = requests.get(f'http://127.0.0.1:{port}/metrics')
        metric_families = list(text_string_to_metric_families(metrics_response.text))
        samples = [y for x in metric_families for y in x.samples]

        assert Sample(
            name='routemaster_api_request_duration_seconds_count',
            labels={'method': 'GET', 'status': '200', 'endpoint': '/'},
            value=1.0,
        ) in samples


def test_prometheus_logger_ignores_metrics_path(routemaster_serve_subprocess):
    with routemaster_serve_subprocess(
        wait_for_output=b'Booting worker',
    ) as (proc, port):
        # This should _not_ populate the metrics with any samples
        requests.get(f'http://127.0.0.1:{port}/metrics')

        metrics_response = requests.get(f'http://127.0.0.1:{port}/metrics')
        metric_families = list(text_string_to_metric_families(metrics_response.text))
        samples = [y for x in metric_families for y in x.samples]

        assert samples == []


def test_prometheus_logger_validates_metrics_path(app):
    orig = os.environ['PROMETHEUS_MULTIPROC_DIR']
    os.environ['PROMETHEUS_MULTIPROC_DIR'] = ''

    with pytest.raises(ValueError):
        PrometheusLogger(app.config)

    os.environ['PROMETHEUS_MULTIPROC_DIR'] = orig
