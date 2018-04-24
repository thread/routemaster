from typing import Any, Dict, Type, Tuple, Iterable

import pytest
import requests

from routemaster.server import server
from routemaster.logging.base import BaseLogger
from routemaster.logging.split_logger import SplitLogger
from routemaster.logging.python_logger import PythonLogger

TEST_CASES: Iterable[Tuple[Type[BaseLogger], Dict[str, Any]]] = [
    (BaseLogger, {}),
    (PythonLogger, {'log_level': 'INFO'}),
    (PythonLogger, {'log_level': 'ERROR'}),
    (SplitLogger, {'loggers': []}),
    (SplitLogger, {'loggers': [
        PythonLogger(None, log_level='WARN'),
    ]}),
    (SplitLogger, {'loggers': [
        PythonLogger(None, log_level='WARN'),
        BaseLogger(None, {}),
    ]}),
)


@pytest.mark.parametrize('logger, kwargs', TEST_CASES)
def test_logger(app, logger, kwargs):
    logger = logger(app.config, **kwargs)
    state_machine = app.config.state_machines['test_machine']
    state = state_machine.states[0]
    feed_url = 'https://localhost'

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
