"""Creation and fetching of feed data."""
import threading
from typing import Any, Dict, Callable, Optional

import requests
from dataclasses import InitVar, dataclass

from routemaster.utils import get_path, template_url


def feeds_for_state_machine(state_machine) -> Dict[str, 'Feed']:
    """Get a mapping of feed prefixes to unfetched feeds."""
    return {
        x.name: Feed(x.url, state_machine.name)  # type: ignore
        for x in state_machine.feeds
    }


class FeedNotFetched(Exception):
    """Raised if we try to access the data in a feed we haven't yot fetched."""
    pass


_feed_sessions = threading.local()


def _get_feed_session():
    # We cache sessions per thread so that we can use `requests.Session`'s
    # underlying `urllib3` connection pooling.
    if not hasattr(_feed_sessions, 'session'):
        _feed_sessions.session = requests.Session()
    return _feed_sessions.session


@dataclass
class Feed:
    """A feed fetcher, able to retreive a feed and read keys out of it."""
    url: str
    state_machine: str
    data: InitVar[Optional[Dict[str, Any]]] = None

    def prefetch(
        self,
        label: str,
        log_response: Callable[[requests.Response], None] = lambda x: None,
    ) -> None:
        """Trigger the fetching of a feed's data."""
        if self.data is not None:
            return

        url = template_url(self.url, self.state_machine, label)

        session = _get_feed_session()
        response = session.get(url)
        log_response(response)
        response.raise_for_status()
        self.data = response.json()

    def lookup(self, path):
        """Lookup data from a feed's contents."""
        if self.data is None:
            raise FeedNotFetched(self.url)
        return get_path(path, self.data)
