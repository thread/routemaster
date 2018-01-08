"""Creation and fetching of feed data."""
from typing import Any, Dict, Optional

import requests
from dataclasses import InitVar, dataclass

from routemaster.utils import get_path


def feeds_for_state_machine(state_machine) -> Dict[str, 'Feed']:
    """Get a mapping of feed prefixes to unfetched feeds."""
    return {
        x.name: Feed(x.url, state_machine.name)  # type: ignore
        for x in state_machine.feeds
    }


class FeedNotFetched(Exception):
    """Raised if we try to access the data in a feed we haven't yot fetched."""
    pass


@dataclass
class Feed:
    """A feed fetcher, able to retreive a feed and read keys out of it."""
    url: str
    state_machine: str
    data: InitVar[Optional[Dict[str, Any]]] = None

    def prefetch(self, label: str):
        """Trigger the fetching of a feed's data."""
        if self.data is not None:
            return

        url = self.url.replace(
            '<label>',
            label,
        ).replace(
            '<state_machine>',
            self.state_machine,
        )

        response = requests.get(url)
        response.raise_for_status()
        self.data = response.json()

    def lookup(self, path):
        """Lookup data from a feed's contents."""
        if self.data is None:
            raise FeedNotFetched(self.url)
        return get_path(path, self.data)
