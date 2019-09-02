"""Helpers for working with time."""

import datetime


def time_appears_in_range(
    when: datetime.time,
    start: datetime.datetime,
    end: datetime.datetime,
) -> bool:
    """
    Determine whether the given time appears within the given time range.

    Note: the comparison does not include the start instant, but does include
    the end instant.
    """
    if (end - start) >= datetime.timedelta(days=1):
        return True

    date = start.date() if when > start.time() else end.date()

    instant = datetime.datetime.combine(date, when)

    return start < instant <= end
