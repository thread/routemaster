"""Periodic job running."""

import time
import logging
import threading
from typing import Callable, NamedTuple

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
from routemaster.state_machine import (
    IsExitingCheck,
    StateProcessor,
    process_gate_trigger,
    process_action_retries,
    process_gate_metadata_retries,
)

logger = logging.getLogger(__name__)


class _Process(NamedTuple):
    fn: StateProcessor
    state: State
    app: App
    state_machine: StateMachine
    is_terminating: IsExitingCheck

    def __call__(self):
        name = getattr(self.fn, '__name__', 'process')
        logger.info(
            f"Started cron {name} for state {self.state.name} in "
            f"{self.state_machine.name}",
        )

        try:
            time_start = time.time()
            self.fn(
                self.app,
                self.state,
                self.state_machine,
                self.is_terminating,
            )
            duration = time.time() - time_start
        except Exception as e:
            print(e)

        logger.info(
            f"Completed cron {name} for state {self.state.name} "
            f"in {self.state_machine.name} in {duration:.2f} seconds",
        )

    def __repr__(self):
        return self.fn.__name__


def _configure_schedule_for_state_machine(
    app: App,
    scheduler: schedule.Scheduler,
    state_machine: StateMachine,
    is_terminating: Callable[[], bool],
) -> None:
    process_args = (app, state_machine, is_terminating)

    for state in state_machine.states:
        if isinstance(state, Action):
            scheduler.every().minute.do(
                _Process(process_action_retries, state, *process_args),
            )

        elif isinstance(state, Gate):
            for trigger in state.triggers:
                if isinstance(trigger, TimeTrigger):
                    scheduler.every().day.at(
                        f"{trigger.time.hour:02d}:{trigger.time.minute:02d}",
                    ).do(
                        _Process(process_gate_trigger, state, *process_args),
                    )
                elif isinstance(trigger, IntervalTrigger):
                    scheduler.every(
                        trigger.interval.total_seconds(),
                    ).seconds.do(
                        _Process(process_gate_trigger, state, *process_args),
                    )
                elif isinstance(trigger, MetadataTrigger):
                    scheduler.every().minute.do(
                        _Process(
                            process_gate_metadata_retries,
                            state,
                            *process_args,
                        ),
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
        super().__init__(name="cron")

    def run(self) -> None:
        """Run main scheduling loop."""
        configure_schedule(self.app, self.scheduler, self.is_terminating)
        logger.info("Starting cron thread")
        while not self.is_terminating():
            self.scheduler.run_pending()
            time.sleep(1)

    def stop(self) -> None:
        """Set the stopping flag and wait for thread end."""
        self._terminating = True
        logger.info("Cron thread shutting down")
        self.join()

    def is_terminating(self) -> bool:
        """Dynamically access whether we are terminating."""
        return self._terminating
