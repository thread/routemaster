"""Core App singleton that holds state for the application."""
import threading
from typing import Dict

from sqlalchemy.engine import Engine

from routemaster.db import initialise_db
from routemaster.config import Config, StateMachine
from routemaster.logging import BaseLogger, SplitLogger, register_loggers
from routemaster.webhooks import (
    WebhookRunner,
    webhook_runner_for_state_machine,
)


class App(threading.local):
    """Core application state."""

    db: Engine
    config: Config
    logger: BaseLogger
    _webhook_runners: Dict[StateMachine, WebhookRunner]

    def __init__(
        self,
        config: Config,
    ) -> None:
        """Initialisation of the app state."""
        self.config = config
        self.db = initialise_db(self.config.database)

        self.logger = SplitLogger(config, loggers=register_loggers(config))

        # Webhook runners may choose to persist a session, so we instantiate
        # up-front to ensure we re-use state.
        self._webhook_runners = {
            x: webhook_runner_for_state_machine(y)
            for x, y in self.config.state_machines.items()
        }

    def get_webhook_runner(self, state_machine: StateMachine) -> WebhookRunner:
        """Get the webhook runner for a state machine."""
        return self._webhook_runners.get(state_machine.name)
