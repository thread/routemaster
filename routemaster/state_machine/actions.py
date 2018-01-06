"""Action (webhook invocation) evaluator."""

import json

from sqlalchemy import func

from routemaster.db import history
from routemaster.app import App
from routemaster.config import Gate, Action, StateMachine
from routemaster.webhooks import (
    WebhookResult,
    webhook_runner_for_state_machine,
)
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    _lock_label,
    _choose_next_state,
    _context_for_label,
    _get_current_state,
    _get_state_machine,
    _get_label_metadata,
    _labels_to_retry_for_action,
)


def transactional_process_action(app: App, label: LabelRef) -> bool:
    """
    Process the action for a label.

    Transactional wrapper with required locking, around `process_action`.

    Raises a TypeError when the current state is not an action.
    """
    state_machine = _get_state_machine(app, label)

    with app.db.begin() as conn:
        _lock_label(label, conn)
        current_state = _get_current_state(label, state_machine, conn)
        if not isinstance(current_state, Gate):
            raise TypeError("Label not in an action state")
        return process_action(app, current_state, label, conn)


def process_action(app: App, action: Action, label: LabelRef, conn) -> bool:
    """
    Process an action for a label.

    Assumes that `action` is the current state of the label, and that the label
    has been locked.

    Returns whether the label progressed in the state machine, for which `True`
    implies further progression should be attempted.
    """
    state_machine = _get_state_machine(app, label)
    metadata = _get_label_metadata(label, state_machine, conn)

    webhook_data = json.dumps({
        'metadata': metadata,
        'label': label.name,
    }, sort_keys=True).encode('utf-8')

    run_webhook = webhook_runner_for_state_machine(state_machine)

    result = run_webhook(
        action.webhook,
        'application/json',
        webhook_data,
    )

    if result != WebhookResult.SUCCESS:
        return False

    context = _context_for_label(label, metadata, state_machine, action)
    next_state = _choose_next_state(state_machine, action, context)

    conn.execute(history.insert().values(
        label_state_machine=state_machine.name,
        label_name=label.name,
        created=func.now(),
        old_state=action.name,
        new_state=next_state,
    ))

    return True


def process_retries(
    app: App,
    state_machine: StateMachine,
    action: Action,
) -> None:
    """
    Cron retry entrypoint. This will retry all labels in a given action.
    """
    with app.db.begin() as conn:
        relevant_labels = _labels_to_retry_for_action(
            state_machine,
            action,
            conn,
        )

        for label_name, metadata in relevant_labels.items():
            label = LabelRef(name=label_name, state_machine=state_machine.name)

            with conn.begin() as savepoint:
                process_action(
                    app,
                    action,
                    label,
                    savepoint,
                )
