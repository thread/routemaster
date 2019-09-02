import datetime

import dateutil.tz

from routemaster.time_utils import time_appears_in_range

London = dateutil.tz.gettz('Europe/London')
Paris = dateutil.tz.gettz('Europe/Paris')


def test_time_appears_in_same_day_range() -> None:
    when = datetime.time(12, 0)
    start = datetime.datetime(2019, 1, 1, 11, 0)
    end = datetime.datetime(2019, 1, 1, 13, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is True


def test_time_doesnt_appear_in_same_day_range_when_before() -> None:
    when = datetime.time(2, 0)
    start = datetime.datetime(2019, 1, 1, 11, 0)
    end = datetime.datetime(2019, 1, 1, 13, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is False


def test_time_doesnt_appear_in_same_day_range_when_after() -> None:
    when = datetime.time(16, 0)
    start = datetime.datetime(2019, 1, 1, 11, 0)
    end = datetime.datetime(2019, 1, 1, 13, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is False


def test_time_appears_in_cross_day_range_later_first_day() -> None:
    when = datetime.time(23, 0)
    start = datetime.datetime(2019, 1, 1, 22, 0)
    end = datetime.datetime(2019, 1, 2, 2, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is True


def test_time_appears_in_cross_day_range_early_second_day() -> None:
    when = datetime.time(1, 0)
    start = datetime.datetime(2019, 1, 1, 22, 0)
    end = datetime.datetime(2019, 1, 2, 2, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is True


def test_time_doesnt_appear_in_cross_day_range() -> None:
    when = datetime.time(12, 0)
    start = datetime.datetime(2019, 1, 1, 22, 0)
    end = datetime.datetime(2019, 1, 2, 2, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is False


def test_time_appears_in_multi_day_range_later_first_day() -> None:
    when = datetime.time(23, 0)
    start = datetime.datetime(2019, 1, 1, 22, 0)
    end = datetime.datetime(2019, 1, 3, 2, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is True


def test_time_appears_in_multi_day_range_early_last_day() -> None:
    when = datetime.time(1, 0)
    start = datetime.datetime(2019, 1, 1, 22, 0)
    end = datetime.datetime(2019, 1, 3, 2, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is True


def test_time_appears_in_multi_day_range_when_appears_outside() -> None:
    when = datetime.time(12, 0)
    start = datetime.datetime(2019, 1, 1, 22, 0)
    end = datetime.datetime(2019, 1, 3, 2, 0)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is True


def test_time_appears_in_same_day_range_different_timezones() -> None:
    when = datetime.time(12, 30, tzinfo=Paris)
    start = datetime.datetime(2019, 1, 1, 11, 20, tzinfo=London)
    end = datetime.datetime(2019, 1, 1, 11, 40, tzinfo=London)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is True


def test_time_doesnt_appear_in_same_day_range_when_before_different_timezones() -> None:
    when = datetime.time(12, 0, tzinfo=Paris)
    start = datetime.datetime(2019, 1, 1, 11, 20, tzinfo=London)
    end = datetime.datetime(2019, 1, 1, 11, 40, tzinfo=London)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is False


def test_time_doesnt_appear_in_same_day_range_when_after_different_timezones() -> None:
    when = datetime.time(12, 50, tzinfo=Paris)
    start = datetime.datetime(2019, 1, 1, 11, 20, tzinfo=London)
    end = datetime.datetime(2019, 1, 1, 11, 40, tzinfo=London)

    in_range = time_appears_in_range(when, start, end)

    assert in_range is False
