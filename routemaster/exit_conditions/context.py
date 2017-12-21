"""Context definition for exit condition programs."""

from routemaster.utils import get_path
from routemaster.exit_conditions.exceptions import UndefinedVariable


class Context(object):
    """Execution context for exit condition programs."""

    def __init__(self, metadata, now, feeds=None):
        """Create an execution context."""
        if now.tzinfo is None:
            raise ValueError(
                "Cannot evaluate exit conditions with naive datetimes",
            )

        self.now = now
        self.metadata = metadata
        self.feeds = feeds

    def lookup(self, path):
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

    def property_handler(self, property_name, value, **kwargs):
        if property_name == ('passed',):
            epoch = kwargs['since']
            return (self.now - epoch).total_seconds() >= value
        if property_name == ('defined',):
            return value is not None
        if property_name == () and 'in' in kwargs:
            return value in kwargs['in']
        raise ValueError("Unknown property {name}".format(
            name='.'.join(property_name)),
        )
