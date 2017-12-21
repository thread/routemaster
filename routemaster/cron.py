"""Periodic job running."""

import time
import schedule

from routemaster.app import App
from routemaster.config import StateMachine, Action, Gate, TimeTrigger

import threading


class CronThread(threading.Thread):
    """Background thread for running periodic jobs."""

    def __init__(self, app: App) -> None:
        self.terminating = False
        self.app = app
        self.scheduler = schedule.Scheduler()
        super().__init__(name="cron", daemon=True)

    def _trigger_action(self, action: Action) -> None:
        print(f"Processing action {action.name}")

    def _trigger_gate(self, gate: Gate) -> None:
        print(f"Processing gate {gate.name}")

    def _configure_schedule_for_state_machine(
        self,
        state_machine: StateMachine,
    ) -> None:
        for state in state_machine.states:
            if isinstance(state, Action):
                self.scheduler.every().minute.do(
                    self._trigger_action,
                    state,
                )
                pass
            elif isinstance(state, Gate):
                for trigger in state.triggers:
                    if isinstance(trigger, TimeTrigger):
                        self.scheduler.every().day.at(
                            f"{trigger.time.hour:02d}:{trigger.time.minute:02d}",
                        ).do(
                            self._trigger_gate,
                            state,
                        )

    def _configure_schedule(self) -> None:
        """Set up all scheduled tasks that need running."""
        for state_machine in self.app.config.state_machines.values():
            self._configure_schedule_for_state_machine(state_machine)

    def run(self) -> None:
        """Run main scheduling loop."""
        self._configure_schedule()
        while not self.terminating:
            self.scheduler.run_pending()
            time.sleep(1)

    def stop(self) -> None:
        """Set the stopping flag and wait for thread end."""
        self.terminating = True
        self.join()
