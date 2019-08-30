"""Processor classes to support cron scheduled jobs."""

import logging
import functools
from typing import Any, Type, Callable

from typing_extensions import Protocol

from routemaster.config import (
    TimezoneAwareTrigger,
    MetadataTimezoneAwareTrigger,
)
from routemaster.timezones import where_is_this_the_time
from routemaster.state_machine import (
    LabelProvider,
    labels_in_state_with_metadata,
)


def _logger_for_type(type_: Type[Any]) -> logging.Logger:
    return logging.getLogger(f"({type_.__module__}.{type_.__name__}")


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

    This expects to be called regularly and it will only actually do any
    processing if the time is correct for its' trigger timezone.
    """
    def __init__(
        self,
        processor: Callable[[], None],
        trigger: TimezoneAwareTrigger,
    ) -> None:
        self.processor = processor
        self.trigger = trigger
        self._logger = _logger_for_type(type(self))

    def __call__(self) -> None:
        """Run the cron processing."""
        timezones = where_is_this_the_time(self.trigger.time)

        if self.trigger.timezone not in timezones:
            self._logger.debug(
                f"Not currently time to do processing (waiting for "
                f"{self.trigger.time} in {self.trigger.timezone})",
                extra={
                    'timezones': timezones,
                },
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

    This expects to be called regularly and it will only actually do any
    processing if the time is correct for any known timezone. The processing it
    does is then filtered to labels whose timezone metadata is among the
    matched timezones.
    """
    def __init__(
        self,
        processor: ProcessingSpecificCronProcessor,
        trigger: MetadataTimezoneAwareTrigger,
    ) -> None:
        self.processor = processor
        self.trigger = trigger
        self._logger = _logger_for_type(type(self))

    def __call__(self) -> None:
        """Run the cron processing."""
        timezones = where_is_this_the_time(self.trigger.time)

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
