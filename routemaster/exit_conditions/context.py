"""Context definition for exit condition programs."""

from routemaster.utils import get_path
from routemaster.exit_conditions.exceptions import UndefinedVariable


class Context(object):
    """Execution context for exit condition programs."""

    def __init__(self, metadata, feeds=None):
        """Create an execution context."""
        self.metadata = metadata
        self.feeds = feeds

    def get_path(self, path):
        """Look up a path in the execution context."""
        location, *rest = path

        try:
            return {
                'metadata': lambda p: get_path(p, self.metadata)
            }[location](rest)
        except KeyError:
            raise UndefinedVariable(
                f"Variable at '{'.'.join(path)}' is undefined"
            )
