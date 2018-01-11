"""Periodic job running."""

import time
import threading
from typing import Callable

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
from routemaster.state_machine import process_action_retries

IsExitingCheck = Callable[[], bool]
CronProcessor = Callable[
    [App, State, StateMachine, IsExitingCheck],
    None,
]


def _retry_action(app, state, state_machine, should_terminate) -> None:
    print(f"Processing action retries for {state.name}")
    process_action_retries(app, state, state_machine, should_terminate)


def _trigger_gate(app, state, state_machine, should_terminate) -> None:
    print(f"Processing interval/time trigger for {state.name}")


def _retry_metadata_updates(
    app,
    state,
    state_machine,
    should_terminate,
) -> None:
    print(f"Processing metadata update trigger for {state.name}")


def _process(
    fn: CronProcessor,
    state: State,
    app: App,
    state_machine: StateMachine,
    is_terminating: IsExitingCheck,
) -> None:
    try:
        fn(app, state, state_machine, is_terminating)
    except Exception as e:
        print(e)


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
                _process,
                _retry_action,
                state,
                *process_args,
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
                        *process_args,
                    )
                elif isinstance(trigger, IntervalTrigger):
                    scheduler.every(
                        trigger.interval.total_seconds(),
                    ).seconds.do(
                        _process,
                        _trigger_gate,
                        state,
                        *process_args,
                    )
                elif isinstance(trigger, MetadataTrigger):
                    scheduler.every(60).seconds.do(
                        _process,
                        _retry_metadata_updates,
                        state,
                        *process_args,
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
