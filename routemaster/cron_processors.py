"""Processor classes to support cron scheduled jobs."""

import functools
from typing import Callable

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

    def __call__(self) -> None:
        """Run the cron processing."""
        timezones = where_is_this_the_time(self.trigger.time)

        if self.trigger.timezone not in timezones:
            return

        self.processor()


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

    def __call__(self) -> None:
        """Run the cron processing."""
        timezones = where_is_this_the_time(self.trigger.time)

        if not timezones:
            return

        label_provider = functools.partial(
            labels_in_state_with_metadata,
            path=self.trigger.timezone_metadata_path,
            values=timezones,
        )

        self.processor(label_provider=label_provider)
