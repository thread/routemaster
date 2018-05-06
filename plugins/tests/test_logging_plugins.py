import os
import socket
import pathlib
import contextlib
import subprocess
from typing import Any, Dict, Type, Tuple, Iterable

import pytest
import requests
from flask import Flask
from routemaster_sentry import SentryLogger
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

TEST_CASES: Iterable[Tuple[Type[BaseLogger], Dict[str, Any]]] = [
    (SentryLogger, SENTRY_KWARGS),
    (PrometheusLogger, PROMETHEUS_KWARGS),
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

    logger.debug("test")
    logger.info("test")
    logger.warning("test")
    logger.error("test")
    logger.critical("test")
    logger.exception("test")

    with pytest.raises(AttributeError):
        logger.non_existent_logging_fn("test")

    response = requests.Response()
    logger.webhook_response(state_machine, state, response)
    logger.feed_response(state_machine, state, feed_url, response)


def test_prometheus_logger_wipes_directory_on_startup(app):
    tmp = pathlib.Path(os.environ['prometheus_multiproc_dir'])
    tmp.mkdir(parents=True, exist_ok=True)

    filepath = tmp / 'foo.txt'
    dirpath = tmp / 'subdir'

    dirpath.mkdir(parents=True, exist_ok=True)
    with filepath.open('w') as f:
        f.write('Hello, world')

    PrometheusLogger(app.config)

    assert not filepath.exists()
    assert not dirpath.exists()


def test_prometheus_logger_metrics():
    # Get a free port
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]

    try:
        proc = subprocess.Popen(
            f'routemaster --config-file=example.yaml serve --bind 127.0.0.1:{port}',
            shell=True,
            stderr=subprocess.PIPE,
        )
        while True:
            if 'Booting worker' in proc.stderr.readline().decode('utf-8'):
                break

        # Populate metrics with a request
        requests.get(f'http://127.0.0.1:{port}/')

        metrics_response = requests.get(f'http://127.0.0.1:{port}/metrics')
        metric_families = list(text_string_to_metric_families(metrics_response.text))
        samples = [y for x in metric_families for y in x.samples]

        assert (
            'routemaster_api_request_duration_seconds_count',
            {'method': 'GET', 'status': '200', 'endpoint': '/'},
            1.0,
        ) in samples
    finally:
        proc.kill()


def test_prometheus_logger_ignores_metrics_path(custom_app, custom_client):
    # Get a free port
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]

    try:
        proc = subprocess.Popen(
            f'routemaster --config-file=example.yaml serve --bind 127.0.0.1:{port}',
            shell=True,
            stderr=subprocess.PIPE,
        )
        while True:
            if 'Booting worker' in proc.stderr.readline().decode('utf-8'):
                break

        # This should _not_ populate the metrics with any samples
        requests.get(f'http://127.0.0.1:{port}/metrics')

        metrics_response = requests.get(f'http://127.0.0.1:{port}/metrics')
        metric_families = list(text_string_to_metric_families(metrics_response.text))
        samples = [y for x in metric_families for y in x.samples]

        assert samples == []
    finally:
        proc.kill()


def test_prometheus_logger_validates_metrics_path(app):
    orig = os.environ['prometheus_multiproc_dir']
    os.environ['prometheus_multiproc_dir'] = ''

    with pytest.raises(ValueError):
        PrometheusLogger(app.config)

    os.environ['prometheus_multiproc_dir'] = orig
