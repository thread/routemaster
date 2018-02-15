import pytest

from routemaster.logging.base import BaseLogger
from routemaster.logging.split_logger import SplitLogger
from routemaster.logging.python_logger import PythonLogger

TEST_CASES = (
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
def test_logger(app_config, logger, kwargs):
    logger = logger(app_config.config, **kwargs)
    state_machine = app_config.config.state_machines['test_machine']
    state = state_machine.states[0]
    feed_url = 'https://localhost'

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

    logger.debug("test")
    logger.info("test")
    logger.warning("test")
    logger.error("test")
    logger.critical("test")
    logger.exception("test")