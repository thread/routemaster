import datetime
from unittest import mock

import freezegun

from routemaster.config import (
    TimezoneAwareTrigger,
    MetadataTimezoneAwareTrigger,
)
from routemaster.state_machine import labels_in_state_with_metadata
from routemaster.cron_processors import (
    TimezoneAwareProcessor,
    MetadataTimezoneAwareProcessor,
)

# Test TimezoneAwareProcessor


@freezegun.freeze_time('2019-08-01 12:00 UTC')
def test_timezone_aware_processor_runs_on_time() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Etc/UTC')

    processor = TimezoneAwareProcessor(mock_callable, trigger)
    processor()

    mock_callable.assert_called_once_with()


@freezegun.freeze_time('2019-08-01 12:00 UTC')
def test_timezone_aware_processor_runs_on_time_other_timezone() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(13, 0), 'Europe/London')

    processor = TimezoneAwareProcessor(mock_callable, trigger)
    processor()

    mock_callable.assert_called_once_with()


@freezegun.freeze_time('2019-08-01 12:00 UTC')
def test_timezone_aware_processor_doesnt_run_when_timezone_doesnt_match() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Europe/London')

    processor = TimezoneAwareProcessor(mock_callable, trigger)
    processor()

    mock_callable.assert_not_called()


@freezegun.freeze_time('2019-08-01 15:00 UTC')
def test_timezone_aware_processor_doesnt_run_at_wrong_time() -> None:
    mock_callable = mock.Mock()
    trigger = TimezoneAwareTrigger(datetime.time(12, 0), 'Etc/UTC')

    processor = TimezoneAwareProcessor(mock_callable, trigger)
    processor()

    mock_callable.assert_not_called()


# Test MetadataTimezoneAwareProcessor


@freezegun.freeze_time('2019-01-01 12:00 UTC')
def test_metadata_timezone_aware_processor_runs_on_time() -> None:
    mock_callable = mock.Mock()
    trigger = MetadataTimezoneAwareTrigger(datetime.time(12, 0), ['tz'])

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

    processor = MetadataTimezoneAwareProcessor(mock_callable, trigger)

    with mock.patch('functools.partial') as mock_partial:
        processor()

    mock_partial.assert_not_called()
    mock_callable.assert_not_called()
