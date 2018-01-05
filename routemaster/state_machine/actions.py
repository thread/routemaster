"""Action (webhook invocation) evaluator."""

import json

from sqlalchemy import and_, func, select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.feeds import feeds_for_state_machine
from routemaster.config import Gate, Action, StateMachine
from routemaster.context import Context
from routemaster.webhooks import (
    WebhookResult,
    WebhookRunner,
    _webhook_runner_for_state_machine,
)
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    _utcnow,
    _lock_label,
    _choose_next_state,
    _get_current_state,
    _get_state_machine,
    _get_label_metadata,
    _labels_to_retry_for_action,
)
from routemaster.state_machine.exceptions import DeletedLabel


def transactional_process_action(app: App, label: LabelRef) -> bool:
    """
    Process the action for a label.

    Transactional wrapper with required locking, around `process_action`.

    Raises a TypeError when the current state is not an action.
    """


def process_action(app: App, action: Action, label: LabelRef, conn) -> bool:
    """
    Process an action for a label.

    Assumes that `action` is the current state of the label, and that the label
    has been locked.

    Returns whether the label progressed in the state machine, for which `True`
    implies further progression should be attempted.
    """
    state_machine = _get_state_machine(app, label)

    webhook_data = json.dumps({
        'metadata': metadata,
        'label': label_name,
    }, sort_keys=True).encode('utf-8')

    result = run_webhook(
        action.webhook,
        'application/json',
        webhook_data,
    )

    if result == WebhookResult.SUCCESS:
        next_state = _choose_next_state(state_machine, action, context)

        conn.execute(history.insert().values(
            label_state_machine=state_machine.name,
            label_name=label.name,
            created=func.now(),
            old_state=action.name,
            new_state=next_state,
        ))

        return True


def process_retries(action: Action):
    """
    Cron retry entrypoint. This will retry all labels in a given action.
    """


def run_action(
    app: App,
    state_machine: StateMachine,
    action: Action,
    run_webhook: WebhookRunner,
) -> None:
    """Run `action` for all outstanding users."""
    with app.db.begin() as conn:
        relevant_labels = _labels_to_retry_for_action(
            state_machine,
            action,
            conn,
        )

        for label_name, metadata in relevant_labels.items():
            process_action(
                app,
                action,
                LabelRef(name=label_name, state_machine=state_machine.name),
                conn,
            )
