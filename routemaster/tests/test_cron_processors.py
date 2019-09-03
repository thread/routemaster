import datetime
from unittest import mock

import freezegun
import dateutil.tz

from routemaster.config import (
    TimezoneAwareTrigger,
    MetadataTimezoneAwareTrigger,
)
from routemaster.state_machine import labels_in_state_with_metadata
from routemaster.cron_processors import (
    TimezoneAwareProcessor,
    MetadataTimezoneAwareProcessor,
)

UTC = dateutil.tz.gettz('UTC')


def recently() -> datetime.datetime:
    """
    Helper for getting a time shortly before now. This is mostly expected to be
    used for the construction of cron processors, so that their construction
    time is separate to (and earlier than) the current time when they're run
    but otherwise very close (to avoid changing the semantics of the test).
    """
    return datetime.datetime.now(UTC) - datetime.timedelta(microseconds=1)


# Test TimezoneAwareProcessor


def test_timezone_aware_processor_repr() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Etc/UTC')

    processor = TimezoneAwareProcessor(mock_callable, trigger)

    assert 'Etc/UTC' in repr(processor)
    assert '12:00' in repr(processor)


@freezegun.freeze_time('2019-08-01 12:00 UTC')
def test_timezone_aware_processor_runs_on_time() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Etc/UTC')

    with freezegun.freeze_time(recently()):
        processor = TimezoneAwareProcessor(mock_callable, trigger)

    processor()

    mock_callable.assert_called_once_with()


@freezegun.freeze_time('2019-08-01 12:00 UTC')
def test_timezone_aware_processor_runs_on_time_other_timezone() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(13, 0), 'Europe/London')

    with freezegun.freeze_time(recently()):
        processor = TimezoneAwareProcessor(mock_callable, trigger)

    processor()

    mock_callable.assert_called_once_with()


@freezegun.freeze_time('2019-08-01 12:00 UTC')
def test_timezone_aware_processor_doesnt_run_when_timezone_doesnt_match() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Europe/London')

    with freezegun.freeze_time(recently()):
        processor = TimezoneAwareProcessor(mock_callable, trigger)

    processor()

    mock_callable.assert_not_called()


@freezegun.freeze_time('2019-08-01 15:00 UTC')
def test_timezone_aware_processor_doesnt_run_at_wrong_time() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Etc/UTC')

    with freezegun.freeze_time(recently()):
        processor = TimezoneAwareProcessor(mock_callable, trigger)

    processor()

    mock_callable.assert_not_called()


@freezegun.freeze_time('2019-08-01 15:00 UTC')
def test_timezone_aware_processor_runs_if_delayed_since_construction() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Etc/UTC')

    with freezegun.freeze_time('2019-08-01 11:00 UTC'):
        processor = TimezoneAwareProcessor(mock_callable, trigger)

    processor()

    mock_callable.assert_called_once_with()


@freezegun.freeze_time('2019-08-01 15:00 UTC')
def test_timezone_aware_processor_runs_if_delayed_since_last_run() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Etc/UTC')

    with freezegun.freeze_time('2019-08-01 01:00 UTC'):
        processor = TimezoneAwareProcessor(mock_callable, trigger)

    with freezegun.freeze_time('2019-08-01 11:00 UTC'):
        processor()

    mock_callable.assert_not_called()  # not yet

    processor()

    mock_callable.assert_called_once_with()


def test_timezone_aware_processor_doesnt_run_multiple_times() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Etc/UTC')

    with freezegun.freeze_time('2019-08-01 01:00 UTC'):
        processor = TimezoneAwareProcessor(mock_callable, trigger)

    with freezegun.freeze_time('2019-08-01 11:00 UTC'):
        processor()

    mock_callable.assert_not_called()  # not yet

    with freezegun.freeze_time('2019-08-01 15:00 UTC') as frozen_time:
        processor()
        frozen_time.tick(delta=datetime.timedelta(microseconds=10))
        processor()

    mock_callable.assert_called_once_with()


# Test MetadataTimezoneAwareProcessor


def test_metadata_timezone_aware_processor_repr() -> None:
    mock_callable = mock.Mock()
    trigger = MetadataTimezoneAwareTrigger(datetime.time(12, 0), ['tz'])

    with freezegun.freeze_time(recently()):
        processor = MetadataTimezoneAwareProcessor(mock_callable, trigger)

    assert 'tz' in repr(processor)
    assert '12:00' in repr(processor)


@freezegun.freeze_time('2019-01-01 12:00 UTC')
def test_metadata_timezone_aware_processor_runs_on_time() -> None:
    mock_callable = mock.Mock()
    trigger = MetadataTimezoneAwareTrigger(datetime.time(12, 0), ['tz'])

    with freezegun.freeze_time(recently()):
        processor = MetadataTimezoneAwareProcessor(mock_callable, trigger)

    with mock.patch('functools.partial') as mock_partial:
        processor()

        mock_partial.assert_called_once_with(
            labels_in_state_with_metadata,
            path=['tz'],
            values=mock.ANY,
        )

    timezones = mock_partial.call_args[1]['values']

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' in timezones

    mock_callable.assert_called_once_with(label_provider=mock.ANY)


@freezegun.freeze_time('2019-08-01 12:00 UTC')
def test_metadata_timezone_aware_processor_runs_on_time_other_timezone() -> None:
    mock_callable = mock.Mock()
    trigger = MetadataTimezoneAwareTrigger(datetime.time(13, 0), ['tz'])

    with freezegun.freeze_time(recently()):
        processor = MetadataTimezoneAwareProcessor(mock_callable, trigger)

    with mock.patch('functools.partial') as mock_partial:
        processor()

        mock_partial.assert_called_once_with(
            labels_in_state_with_metadata,
            path=['tz'],
            values=mock.ANY,
        )

    timezones = mock_partial.call_args[1]['values']

    assert 'Etc/UTC' not in timezones
    assert 'Europe/London' in timezones

    mock_callable.assert_called_once_with(label_provider=mock.ANY)


@freezegun.freeze_time('2019-08-01 12:05 UTC')
def test_metadata_timezone_processor_doesnt_run_at_wrong_time() -> None:
    mock_callable = mock.Mock()
    trigger = MetadataTimezoneAwareTrigger(datetime.time(12, 0), ['tz'])

    with freezegun.freeze_time(recently()):
        processor = MetadataTimezoneAwareProcessor(mock_callable, trigger)

    with mock.patch('functools.partial') as mock_partial:
        processor()

    mock_partial.assert_not_called()
    mock_callable.assert_not_called()


@freezegun.freeze_time('2019-08-01 12:05 UTC')
def test_metadata_timezone_processor_runs_if_delayed_since_construction() -> None:
    mock_callable = mock.Mock()
    trigger = MetadataTimezoneAwareTrigger(datetime.time(12, 0), ['tz'])

    with freezegun.freeze_time('2019-08-01 11:59 UTC'):
        processor = MetadataTimezoneAwareProcessor(mock_callable, trigger)

    with mock.patch('functools.partial') as mock_partial:
        processor()

        mock_partial.assert_called_once_with(
            labels_in_state_with_metadata,
            path=['tz'],
            values=mock.ANY,
        )

    timezones = mock_partial.call_args[1]['values']

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' not in timezones

    mock_callable.assert_called_once_with(label_provider=mock.ANY)


@freezegun.freeze_time('2019-08-01 12:05 UTC')
def test_metadata_timezone_processor_runs_if_delayed_since_last_run() -> None:
    mock_callable = mock.Mock()
    trigger = MetadataTimezoneAwareTrigger(datetime.time(12, 0), ['tz'])

    with freezegun.freeze_time('2019-08-01 11:55 UTC'):
        processor = MetadataTimezoneAwareProcessor(mock_callable, trigger)

    with freezegun.freeze_time('2019-08-01 11:58 UTC'):
        with mock.patch('functools.partial') as mock_partial:
            processor()

            mock_partial.assert_not_called()  # not yet

    with mock.patch('functools.partial') as mock_partial:
        processor()

        mock_partial.assert_called_once_with(
            labels_in_state_with_metadata,
            path=['tz'],
            values=mock.ANY,
        )

    timezones = mock_partial.call_args[1]['values']

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' not in timezones

    mock_callable.assert_called_once_with(label_provider=mock.ANY)


def test_metadata_timezone_processor_doesnt_run_multiply() -> None:
    mock_callable = mock.Mock()
    trigger = MetadataTimezoneAwareTrigger(datetime.time(12, 0), ['tz'])

    with freezegun.freeze_time('2019-08-01 11:58 UTC'):
        processor = MetadataTimezoneAwareProcessor(mock_callable, trigger)

    with freezegun.freeze_time('2019-08-01 12:05 UTC') as frozen_time:
        with mock.patch('functools.partial') as mock_partial:
            processor()
            frozen_time.tick(delta=datetime.timedelta(microseconds=10))
            processor()

            mock_partial.assert_called_once_with(
                labels_in_state_with_metadata,
                path=['tz'],
                values=mock.ANY,
            )

    timezones = mock_partial.call_args[1]['values']

    assert 'Etc/UTC' in timezones
    assert 'Europe/London' not in timezones

    mock_callable.assert_called_once_with(label_provider=mock.ANY)
