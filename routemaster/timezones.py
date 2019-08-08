"""Helpers for working with timezones."""


import datetime
import functools
from typing import Set, Optional, FrozenSet

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


def where_is_this_the_time(
    when: datetime.time,
    delta: datetime.timedelta = datetime.timedelta(minutes=1),
    now: Optional[datetime.datetime] = None,
) -> Set[str]:
    """
    Find timezones that consider wall-clock time `when` to be the current time.

    Optionally takes:
    - a maximum delta between the current and the expected time (defaulting to
      one minute to match the granularity of our triggers)
    - a reference for the reference current time (specified as a timezone-aware
      `datetime.time`)
    """

    if when.tzinfo is not None:
        raise ValueError(
            "May only specify a wall-clock time as timezone naive",
        )

    if now is None:
        now = datetime.datetime.now(dateutil.tz.tzutc())
    elif now.tzinfo is None:
        raise ValueError("May only specify a timezone-aware reference time")

    delta = abs(delta)

    def is_matching_time(timezone: str, reference: datetime.datetime) -> bool:
        tzinfo = dateutil.tz.gettz(timezone)
        local = reference.astimezone(tzinfo)
        # ignore type due to `tzinfo` argument not being in the version of the
        # typeshed we have available.
        desired = datetime.datetime.combine(  # type: ignore
            reference.date(),
            when,
            tzinfo,
        )
        difference = abs(local - desired)
        return difference <= delta

    return set(
        timezone
        for timezone in get_known_timezones()
        if is_matching_time(timezone, now)
    )
