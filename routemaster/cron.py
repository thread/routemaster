"""Periodic job running."""

import time
import threading

import schedule

from routemaster.app import App
from routemaster.config import (
    Gate,
    Action,
    TimeTrigger,
    StateMachine,
    IntervalTrigger,
)


def _trigger_action(action: Action) -> None:
    print(f"Processing action {action.name}")


def _trigger_gate(gate: Gate) -> None:
    print(f"Processing gate {gate.name}")


def _configure_schedule_for_state_machine(
    scheduler: schedule.Scheduler,
    state_machine: StateMachine,
) -> None:
    for state in state_machine.states:
        if isinstance(state, Action):
            scheduler.every().minute.do(
                _trigger_action,
                state,
            )
            pass
        elif isinstance(state, Gate):
            for trigger in state.triggers:
                if isinstance(trigger, TimeTrigger):
                    scheduler.every().day.at(
                        f"{trigger.time.hour:02d}:{trigger.time.minute:02d}",
                    ).do(
                        _trigger_gate,
                        state,
                    )
                elif isinstance(trigger, IntervalTrigger):
                    scheduler.every(
                        trigger.interval.total_seconds()
                    ).seconds.do(
                        _trigger_gate,
                        state,
                    )


def configure_schedule(scheduler: schedule.Scheduler, app: App) -> None:
    """Set up all scheduled tasks that need running."""
    for state_machine in app.config.state_machines.values():
        _configure_schedule_for_state_machine(scheduler, state_machine)


class CronThread(threading.Thread):  # pragma: no cover
    """Background thread for running periodic jobs."""

    def __init__(self, app: App) -> None:
        self.terminating = False
        self.app = app
        self.scheduler = schedule.Scheduler()
        super().__init__(name="cron", daemon=True)

    def run(self) -> None:
        """Run main scheduling loop."""
        configure_schedule(self.scheduler, self.app)
        while not self.terminating:
            self.scheduler.run_pending()
            time.sleep(1)

    def stop(self) -> None:
        """Set the stopping flag and wait for thread end."""
        self.terminating = True
        self.join()
