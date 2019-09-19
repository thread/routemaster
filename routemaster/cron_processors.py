"""Processor classes to support cron scheduled jobs."""

import logging
import datetime
import functools
from typing import Any, List, Type, Callable

import dateutil.tz
from typing_extensions import Protocol

from routemaster.config import (
    TimezoneAwareTrigger,
    MetadataTimezoneAwareTrigger,
)
from routemaster.timezones import get_known_timezones
from routemaster.time_utils import time_appears_in_range
from routemaster.state_machine import (
    LabelProvider,
    labels_in_state_with_metadata,
)


def _logger_for_type(type_: Type[Any]) -> logging.Logger:
    return logging.getLogger(f"{type_.__module__}.{type_.__name__}")


class ProcessingSpecificCronProcessor(Protocol):
    """Type signature for the a processing-specific cron processor callable."""

    def __call__(
        self,
        *,
        label_provider: LabelProvider,
    ) -> None:
        """Type signature for a processing-specific cron processor callable."""
        ...


class TimezoneAwareProcessor:
    """
    Cron processor for the `TimezoneAwareTrigger`.

    This expects to be called regularly, but is tolerant of delays. It will
    only actually do any processing if the time for its trigger timezone has
    passed since it was last called (or constructed).

    Processing of delayed runs has two side-effects:
     - arbitrarily delayed processing will still run, but
     - delayed processing may cause multiple runs whose times have all passed
       between calls to be processed together as a single run
    """
    def __init__(
        self,
        processor: Callable[[], None],
        trigger: TimezoneAwareTrigger,
    ) -> None:
        self.processor = processor
        self.trigger = trigger
        self._last_call = datetime.datetime.now(dateutil.tz.tzutc())
        self._logger = _logger_for_type(type(self))

    def __call__(self) -> None:
        """Run the cron processing."""
        last_call = self._last_call
        self._last_call = now = datetime.datetime.now(dateutil.tz.tzutc())

        trigger_time = self.trigger.time.replace(
            tzinfo=dateutil.tz.gettz(self.trigger.timezone),
        )

        try:
            should_process = time_appears_in_range(
                when=trigger_time,
                start=last_call,
                end=now,
            )
        except ValueError:
            self._logger.exception(
                "Failed to determine whether trigger time has passed",
            )
            return

        if not should_process:
            self._logger.debug(
                f"Not currently time to do processing (waiting for "
                f"{self.trigger.time} in {self.trigger.timezone})",
            )
            return

        self._logger.info(
            f"Processing {self.trigger.time} in {self.trigger.timezone}",
        )
        self.processor()

    def __repr__(self) -> str:
        """Return a useful debug representation."""
        return (
            f'<TimezoneAwareProcessor: {self.trigger.time} in '
            f'{self.trigger.timezone}>'
        )


class MetadataTimezoneAwareProcessor:
    """
    Cron processor for the `MetadataTimezoneAwareTrigger`.

    This expects to be called regularly, but is tolerant of delays. It will
    only actually do any processing if its trigger time (for any known
    timezone) has pased since it was last called (or constructed). The
    processing it does is then filtered to labels whose timezone metadata is
    among the matched timezones.

    Processing of delayed runs has two side-effects:
     - arbitrarily delayed processing will still run, but
     - delayed processing may cause multiple runs whose times have all passed
       between calls to be processed together as a single run
    """
    def __init__(
        self,
        processor: ProcessingSpecificCronProcessor,
        trigger: MetadataTimezoneAwareTrigger,
    ) -> None:
        self.processor = processor
        self.trigger = trigger
        self._last_call = datetime.datetime.now(dateutil.tz.tzutc())
        self._logger = _logger_for_type(type(self))

    def __call__(self) -> None:
        """Run the cron processing."""
        last_call = self._last_call
        self._last_call = now = datetime.datetime.now(dateutil.tz.tzutc())

        try:
            timezones: List[str] = []
            for timezone in get_known_timezones():
                trigger_time = self.trigger.time.replace(
                    tzinfo=dateutil.tz.gettz(timezone),
                )
                matches = time_appears_in_range(
                    when=trigger_time,
                    start=last_call,
                    end=now,
                )
                if matches:
                    timezones.append(timezone)
        except ValueError:
            self._logger.exception(
                "Failed to determine whether trigger time has passed",
            )
            return

        if not timezones:
            self._logger.debug(
                f"Not currently time to do processing (waiting for "
                f"{self.trigger.time})",
            )
            return

        label_provider = functools.partial(
            labels_in_state_with_metadata,
            path=self.trigger.timezone_metadata_path,
            values=timezones,
        )

        self._logger.info(
            f"Processing {self.trigger.time} in {timezones} for "
            f"{self.trigger.timezone_metadata_path}",
        )
        self.processor(label_provider=label_provider)

    def __repr__(self) -> str:
        """Return a useful debug representation."""
        return (
            f'<MetadataTimezoneAwareProcessor: {self.trigger.time} for '
            f'{self.trigger.timezone_metadata_path}>'
        )
