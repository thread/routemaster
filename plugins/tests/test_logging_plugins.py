from typing import Any, Dict, Type, Tuple, Iterable

import pytest
import requests
from flask import Flask
from routemaster_sentry import SentryLogger
from routemaster_prometheus import PrometheusLogger

from routemaster.logging import BaseLogger, SplitLogger

SENTRY_KWARGS = {
    'dsn': 'https://xxxxxxx:xxxxxxx@sentry.io/xxxxxxx',
    'enabled': False,
}
PROMETHEUS_KWARGS = {'path': '/metrics'}

TEST_CASES: Iterable[Tuple[Type[BaseLogger], Dict[str, Any]]] = [
    (SentryLogger, SENTRY_KWARGS),
    (PrometheusLogger, PROMETHEUS_KWARGS),
    (PrometheusLogger, {}),
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

    with logger.process_request({}):
        pass

    with pytest.raises(RuntimeError):
        with logger.process_request({}):
            raise RuntimeError("Error must propagate")

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
