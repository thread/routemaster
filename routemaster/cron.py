"""Periodic job running."""

import time
import threading
import contextlib
from typing import Callable, Iterator

import schedule

from routemaster.app import App
from routemaster.config import (
    Gate,
    State,
    Action,
    TimeTrigger,
    StateMachine,
    IntervalTrigger,
    MetadataTrigger,
)


def _retry_action(app, state, process_part) -> None:
    print(f"Processing action retries for {state.name}")


def _trigger_gate(app, state, process_part) -> None:
    print(f"Processing interval/time trigger for {state.name}")


def _retry_metadata_updates(app, state, process_part) -> None:
    print(f"Processing metadata update trigger for {state.name}")


def _configure_schedule_for_state_machine(
    app: App,
    scheduler: schedule.Scheduler,
    state_machine: StateMachine,
    is_terminating: Callable[[], bool],
) -> None:
    def _process(fn: CronProcessor, state: State) -> None:
        return _process_cron_job(is_terminating, fn, app, state)

    for state in state_machine.states:
        if isinstance(state, Action):
            scheduler.every().minute.do(
                _process,
                _retry_action,
                state,
            )

        elif isinstance(state, Gate):
            for trigger in state.triggers:
                if isinstance(trigger, TimeTrigger):
                    scheduler.every().day.at(
                        f"{trigger.time.hour:02d}:{trigger.time.minute:02d}",
                    ).do(
                        _process,
                        _trigger_gate,
                        state,
                    )
                elif isinstance(trigger, IntervalTrigger):
                    scheduler.every(
                        trigger.interval.total_seconds(),
                    ).seconds.do(
                        _process,
                        _trigger_gate,
                        state,
                    )
                elif isinstance(trigger, MetadataTrigger):
                    scheduler.every(60).seconds.do(
                        _process,
                        _retry_metadata_updates,
                        state,
                    )


def configure_schedule(
    app: App,
    scheduler: schedule.Scheduler,
    is_terminating: Callable[[], bool],
) -> None:
    """Set up all scheduled tasks that need running."""
    for state_machine in app.config.state_machines.values():
        _configure_schedule_for_state_machine(
            app,
            scheduler,
            state_machine,
            is_terminating,
        )


class CronThread(threading.Thread):  # pragma: no cover
    """Background thread for running periodic jobs."""

    def __init__(self, app: App) -> None:
        self._terminating = False
        self.app = app
        self.scheduler = schedule.Scheduler()
        super().__init__(name="cron", daemon=True)

    def run(self) -> None:
        """Run main scheduling loop."""
        configure_schedule(self.app, self.scheduler, self.is_terminating)
        while not self.is_terminating():
            self.scheduler.run_pending()
            time.sleep(1)

    def stop(self) -> None:
        """Set the stopping flag and wait for thread end."""
        self._terminating = True
        self.join()

    def is_terminating(self) -> bool:
        """Dynamically access whether we are terminating."""
        return self._terminating


class StopCronProcessing(Exception):
    """Signal to exit the processing of a series of cron items."""
    pass


ProcessItemContextManager = Callable[
    [],
    contextlib.AbstractContextManager,
]
CronProcessor = Callable[[App, State, ProcessItemContextManager], None]


def _process_cron_job(
    is_terminating: Callable[[], bool],
    fn: CronProcessor,
    app: App,
    state: State,
) -> None:

    @contextlib.contextmanager
    def _inner() -> Iterator[None]:
        try:
            yield
        except Exception as e:
            # Something went wrong in the processing of a single item in the
            # cron queue, log it and allow the processor to continue.
            print(e)
            return

        if is_terminating():
            raise StopCronProcessing()

    try:
        fn(app, state, _inner)
    except StopCronProcessing:
        return
