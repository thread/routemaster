"""Creation and fetching of feed data."""
from typing import Dict

import requests

from routemaster.utils import get_path
from routemaster.config import StateMachine


def feeds_for_state_machine(state_machine: StateMachine) -> Dict[str, 'Feed']:
    """Get a mapping of feed prefixes to unfetched feeds."""
    pass


class FeedNotFetched(Exception):
    """Raised if we try to access the data in a feed we haven't yot fetched."""
    pass


class Feed:
    """A feed fetcher, able to retreive a feed and read keys out of it."""

    def __init__(self, url):
        """Create an un-fetched data feed."""
        self.url = url
        self.data = None

    def fetch(self):
        """Trigger the fetching of a feed's data."""
        response = requests.get(self.url)
        self.data = response.json()

    def lookup(self, path):
        """Lookup data from a feed's contents."""
        if self.data is None:
            raise FeedNotFetched(self.url)
        return get_path(path, self.data)
