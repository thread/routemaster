"""Helpers for working with time."""

import datetime


def time_appears_in_range(
    when: datetime.time,
    start: datetime.datetime,
    end: datetime.datetime,
) -> bool:
    """
    Determine whether the given time appears within the given datetime range.

    Note: the comparison does not include the start instant, but does include
    the end instant.
    """
    if start >= end:
        raise ValueError(
            f"Must be passed a valid range to check (got {start} until {end})",
        )

    if (end - start) >= datetime.timedelta(days=1):
        return True

    date = start.date() if when > start.time() else end.date()

    instant = datetime.datetime.combine(date, when)

    return start < instant <= end
