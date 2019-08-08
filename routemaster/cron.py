"""Periodic job running."""

import time
import functools
import itertools
import threading
from typing import Callable, Iterable

import schedule
from typing_extensions import Protocol

from routemaster.app import App
from routemaster.config import (
    Gate,
    State,
    Action,
    StateMachine,
    IntervalTrigger,
    MetadataTrigger,
    SystemTimeTrigger,
    TimezoneAwareTrigger,
    MetadataTimezoneAwareTrigger,
)
from routemaster.state_machine import (
    LabelProvider,
    LabelStateProcessor,
    process_cron,
    process_gate,
    process_action,
    labels_in_state,
    labels_needing_metadata_update_retry_in_gate,
)
from routemaster.cron_processors import (
    TimezoneAwareProcessor,
    MetadataTimezoneAwareProcessor,
)

IsTerminating = Callable[[], bool]


class CronProcessor(Protocol):
    """Type signature for the cron processor callable."""

    def __call__(
        self,
        *,
        app: App,
        state: State,
        state_machine: StateMachine,
        fn: LabelStateProcessor,
        label_provider: LabelProvider,
    ) -> None:
        """Type signature for the cron processor callable."""
        ...


class StateSpecificCronProcessor(Protocol):
    """Type signature for the a state-specific cron processor callable."""

    def __call__(
        self,
        *,
        fn: LabelStateProcessor,
        label_provider: LabelProvider,
    ) -> None:
        """Type signature for a state-specific cron processor callable."""
        ...


# The cron configuration works by building up a partially applied function
# `process_job`, at multiple levels. This allows us to hook an intermediate
# stage for testing.

def process_job(
    *,
    # Bound at the cron thread level
    is_terminating: IsTerminating,
    # Bound at the state scheduling level
    app: App,
    state: State,
    state_machine: StateMachine,
    # Bound when scheduling a specific job for a state
    fn: LabelStateProcessor,
    label_provider: LabelProvider,
):
    """Process a single instance of a single cron job."""

    def _iter_labels_until_terminating(
        state_machine: StateMachine,
        state: State,
    ) -> Iterable[str]:
        return itertools.takewhile(
            lambda _: not is_terminating(),
            label_provider(app, state_machine, state),
        )

    try:
        with app.logger.process_cron(state_machine, state, fn.__name__):
            process_cron(
                process=fn,
                get_labels=_iter_labels_until_terminating,
                app=app,
                state=state,
                state_machine=state_machine,
            )
    except Exception:
        return


def _configure_schedule_for_state(
    scheduler: schedule.Scheduler,
    processor: StateSpecificCronProcessor,
    state: State,
) -> None:
    if isinstance(state, Action):
        scheduler.every().minute.do(
            processor,
            fn=process_action,
            label_provider=labels_in_state,
        )
    elif isinstance(state, Gate):
        for trigger in state.triggers:
            if isinstance(trigger, SystemTimeTrigger):
                scheduler.every().day.at(
                    f"{trigger.time.hour:02d}:{trigger.time.minute:02d}",
                ).do(
                    processor,
                    fn=process_gate,
                    label_provider=labels_in_state,
                )
            elif isinstance(trigger, TimezoneAwareTrigger):
                func = functools.partial(
                    processor,
                    fn=process_gate,
                    label_provider=labels_in_state,
                )
                scheduler.every().minute.do(
                    TimezoneAwareProcessor(func, trigger),
                )
            elif isinstance(trigger, MetadataTimezoneAwareTrigger):
                scheduler.every().minute.do(
                    MetadataTimezoneAwareProcessor(
                        functools.partial(processor, fn=process_gate),
                        trigger,
                    ),
                )
            elif isinstance(trigger, IntervalTrigger):
                scheduler.every(
                    trigger.interval.total_seconds(),
                ).seconds.do(
                    processor,
                    fn=process_gate,
                    label_provider=labels_in_state,
                )
            elif isinstance(trigger, MetadataTrigger):  # pragma: no branch
                label_provider = labels_needing_metadata_update_retry_in_gate
                scheduler.every().minute.do(
                    processor,
                    fn=process_gate,
                    label_provider=label_provider,
                )
            else:
                # We only care about time based triggers and retries here.
                pass  # pragma: no cover
    else:
        raise RuntimeError(  # pragma: no cover
            f"Unsupported state type {state}",
        )


def configure_schedule(
    app: App,
    scheduler: schedule.Scheduler,
    processor: CronProcessor,
) -> None:
    """Set up all scheduled tasks that need running."""
    for state_machine in app.config.state_machines.values():
        for state in state_machine.states:
            _configure_schedule_for_state(
                scheduler,
                functools.partial(
                    processor,
                    app=app,
                    state=state,
                    state_machine=state_machine,
                ),
                state,
            )


class CronThread(threading.Thread):  # pragma: no cover
    """Background thread for running periodic jobs."""

    def __init__(self, app: App) -> None:
        self._terminating = False
        self.app = app
        self.scheduler = schedule.Scheduler()
        super().__init__(name="cron")

    def run(self) -> None:
        """Run main scheduling loop."""
        configure_schedule(
            self.app,
            self.scheduler,
            functools.partial(
                process_job,
                is_terminating=self.is_terminating,
            ),
        )
        self.app.logger.info("Starting cron thread")
        while not self.is_terminating():
            self.scheduler.run_pending()
            time.sleep(1)

    def stop(self) -> None:
        """Set the stopping flag and wait for thread end."""
        self._terminating = True
        self.app.logger.info("Cron thread shutting down")
        self.join()

    def is_terminating(self) -> bool:
        """Dynamically access whether we are terminating."""
        return self._terminating
