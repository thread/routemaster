"""Context definition for exit condition programs."""

from routemaster.utils import get_path


class Context(object):
    """Execution context for exit condition programs."""

    def __init__(self, metadata, now, feeds, accessed_variables):
        """Create an execution context."""
        if now.tzinfo is None:
            raise ValueError(
                "Cannot evaluate exit conditions with naive datetimes",
            )

        self.now = now
        self.metadata = metadata
        self.feeds = feeds

        self._pre_warm_feeds(accessed_variables)

    def lookup(self, path):
        """Look up a path in the execution context."""
        location, *rest = path

        try:
            return {
                'metadata': self._lookup_metadata,
                'feeds': self._lookup_feed_data,
            }[location](rest)
        except (KeyError, ValueError):
            return None


    def _lookup_metadata(self, path):
        return get_path(path, self.metadata)

    def _lookup_feed_data(self, path):
        feed_name, *rest = path
        return self.feeds[feed_name].lookup(rest)

    def property_handler(self, property_name, value, **kwargs):
        """Handle a property in execution."""
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

    def _pre_warm_feeds(self, accessed_variables):
        for accessed_variable in accessed_variables:
            parts = accessed_variable.split('.')

            if len(parts) < 2:
                continue

            if parts[0] != 'feeds':
                continue

            feed = self.feeds.get(self.feeds[1])
            if feed is not None:
                feed.fetch()
