"""Creation and fetching of feed data."""
from typing import Dict

import requests

from routemaster.utils import get_path


def feeds_for_state_machine(state_machine) -> Dict[str, 'Feed']:
    """Get a mapping of feed prefixes to unfetched feeds."""
    return {x.name: Feed(x.url) for x in state_machine.feeds}


class FeedNotFetched(Exception):
    """Raised if we try to access the data in a feed we haven't yot fetched."""
    pass


class Feed:
    """A feed fetcher, able to retreive a feed and read keys out of it."""

    def __init__(self, url):
        """Create an un-fetched data feed."""
        self.url = url
        self.data = None

    def fetch(self, label: str):
        """Trigger the fetching of a feed's data."""
        if self.data is not None:
            return

        response = requests.get(self.url.replace('<label>', label))
        self.data = response.json()

    def lookup(self, path):
        """Lookup data from a feed's contents."""
        if self.data is None:
            raise FeedNotFetched(self.url)
        return get_path(path, self.data)
