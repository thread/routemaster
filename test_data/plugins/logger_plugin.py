"""Test logger."""

from routemaster.logging import BaseLogger


class TestLogger(BaseLogger):
    """This logger is loaded during tests."""
    def __init__(self, config, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self.kwargs = kwargs


class InvalidLogger(object):
    """
    This logger cannot be loaded.

    It does not inherit from `routemaster.logging.BaseLogger`.
    """
    def __init__(self, *args, **kwargs):
        # Note: args/kwargs needed to not trigger the invalid constructor check
        pass


class NoArgsLogger(BaseLogger):
    """This logger has an invalid constructor."""
    def __init__(self):
        pass


def dynamic_logger(config):
    """This is a callable rather than a class."""
    return BaseLogger(config)


NOT_CALLABLE = 'not callable'
