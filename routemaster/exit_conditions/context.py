"""Context definition for exit condition programs."""

from routemaster.utils import get_path


class Context(object):
    """Execution context for exit condition programs."""

    def __init__(self, metadata, feeds=None):
        """Create an execution context."""
        self.metadata = metadata
        self.feeds = feeds

    def get_path(self, path):
        """Look up a path in the execution context."""
        return get_path(path, self.metadata)
