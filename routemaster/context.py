"""Context definition for exit condition programs."""
import datetime
from typing import Any, Dict, Iterable, Optional, Sequence

from routemaster.feeds import Feed
from routemaster.utils import get_path


class Context(object):
    """Execution context for exit condition programs."""

    def __init__(
        self,
        *,
        label: str,
        metadata: Dict[str, Any],
        now: datetime.datetime,
        feeds: Dict[str, Feed],
        accessed_variables: Iterable[str],
        current_history_entry: Optional[Any],
        feed_logging_context,
    ) -> None:
        """Create an execution context."""
        if now.tzinfo is None:
            raise ValueError(
                "Cannot evaluate exit conditions with naive datetimes",
            )

        self.now = now
        self.metadata = metadata
        self.feeds = feeds
        self.current_history_entry = current_history_entry

        self._pre_warm_feeds(label, accessed_variables, feed_logging_context)

    def lookup(self, path: Sequence[str]) -> Any:
        """Look up a path in the execution context."""
        location, *rest = path

        try:
            return {
                'metadata': self._lookup_metadata,
                'feeds': self._lookup_feed_data,
                'history': self._lookup_history,
            }[location](rest)
        except (KeyError, ValueError):
            return None

    def _lookup_metadata(self, path: Sequence[str]) -> Any:
        return get_path(path, self.metadata)

    def _lookup_feed_data(self, path: Sequence[str]) -> Any:
        feed_name, *rest = path
        return self.feeds[feed_name].lookup(rest)

    def _lookup_history(self, path: Sequence[str]) -> Any:
        if self.current_history_entry is None:
            raise ValueError("Accessed uninitialised variable")

        variable_name, = path
        return {
            'entered_state': self.current_history_entry.created,
            'previous_state': self.current_history_entry.old_state,
        }[variable_name]

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

    def _pre_warm_feeds(
        self,
        label: str,
        accessed_variables: Iterable[str],
        logging_context,
    ):
        for accessed_variable in accessed_variables:
            parts = accessed_variable.split('.')

            if len(parts) < 2:
                continue

            if parts[0] != 'feeds':
                continue

            feed = self.feeds.get(parts[1])
            if feed is not None:
                with logging_context(feed.url) as log_response:
                    feed.prefetch(label, log_response)
