"""Helpers for working with timezones."""


import functools
from typing import FrozenSet

import dateutil.tz
import dateutil.zoneinfo


@functools.lru_cache(maxsize=1)
def get_known_timezones() -> FrozenSet[str]:
    """
    Return a cached set of the known timezones.

    This actually pulls its list from the internal database inside `dateutil`
    as there doesn't seem to be a nice way to pull the data from the system.

    These are expected to change sufficiently infrequently that this is ok. In
    any case, `dateutil` falls back to using this data source anyway, so at
    worst this is a strict subset of the available timezones.
    """
    # Get a non-cached copy of the `ZoneInfoFile`, not because we care about
    # the cache being out of date, but so that we're not stuck with a MB of
    # redundant memory usage.

    # ignore types because `dateutil.zoneinfo` isn't present in the typeshed
    info = dateutil.zoneinfo.ZoneInfoFile(  # type: ignore
        dateutil.zoneinfo.getzoneinfofile_stream(),  # type: ignore
    )

    return frozenset(info.zones.keys())
