import datetime

import freezegun
import dateutil.tz
from pytest import raises

from routemaster.timezones import get_known_timezones, where_is_this_the_time

UTC = dateutil.tz.gettz('UTC')


def test_smoke_get_known_timezones():
    get_known_timezones()


def test_reject_tz_aware_when() -> None:
    when = datetime.time(12, 0, tzinfo=UTC)
    with raises(ValueError):
        where_is_this_the_time(when)


def test_reject_tz_naive_reference() -> None:
    when = datetime.time(12, 0)
    reference = datetime.datetime(2019, 8, 1, 12, 0)
    with raises(ValueError):
        where_is_this_the_time(when, now=reference)


@freezegun.freeze_time('2019-08-01 12:00')
def test_matches_utc() -> None:
    timezones = where_is_this_the_time(datetime.time(12, 0))

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' not in timezones


def test_matches_utc_with_reference() -> None:
    timezones = where_is_this_the_time(
        datetime.time(12, 0),
        now=datetime.datetime(2019, 8, 1, 12, 0, tzinfo=UTC),
    )

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' not in timezones


def test_matches_within_delta_before() -> None:
    timezones = where_is_this_the_time(
        datetime.time(12, 1),
        delta=datetime.timedelta(seconds=5),
        now=datetime.datetime(2019, 1, 1, 12, 0, 58, tzinfo=UTC),
    )

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' in timezones


def test_matches_within_delta_after() -> None:
    timezones = where_is_this_the_time(
        datetime.time(12, 0),
        delta=datetime.timedelta(seconds=5),
        now=datetime.datetime(2019, 1, 1, 12, 0, 2, tzinfo=UTC),
    )

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' in timezones


def test_no_matches_outside_delta_before() -> None:
    timezones = where_is_this_the_time(
        datetime.time(12, 1),
        delta=datetime.timedelta(seconds=1),
        now=datetime.datetime(2019, 1, 1, 12, 0, 58, tzinfo=UTC),
    )

    assert 'Etc/UTC' not in timezones
    assert 'Europe/London' not in timezones


def test_no_matches_outside_delta_after() -> None:
    timezones = where_is_this_the_time(
        datetime.time(12, 0),
        delta=datetime.timedelta(seconds=1),
        now=datetime.datetime(2019, 1, 1, 12, 0, 2, tzinfo=UTC),
    )

    assert 'Etc/UTC' not in timezones
    assert 'Europe/London' not in timezones


def test_match_bst_reference() -> None:
    london_timezone = dateutil.tz.gettz('Europe/London')

    timezones = where_is_this_the_time(
        datetime.time(12, 0),
        now=datetime.datetime(2019, 8, 1, 12, 0, tzinfo=london_timezone),
    )

    assert 'Etc/UTC' not in timezones
    assert 'Europe/London' in timezones


def test_match_gmt_reference() -> None:
    london_timezone = dateutil.tz.gettz('Europe/London')

    timezones = where_is_this_the_time(
        datetime.time(12, 0),
        now=datetime.datetime(2019, 1, 1, 12, 0, tzinfo=london_timezone),
    )

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' in timezones


def test_match_bst_time() -> None:
    timezones = where_is_this_the_time(
        datetime.time(12, 0),
        now=datetime.datetime(2019, 8, 1, 11, 0, tzinfo=UTC),
    )

    assert 'Etc/UTC' not in timezones
    assert 'Europe/London' in timezones


def test_match_gmt_time() -> None:
    timezones = where_is_this_the_time(
        datetime.time(12, 0),
        now=datetime.datetime(2019, 1, 1, 12, 0, tzinfo=UTC),
    )

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' in timezones
