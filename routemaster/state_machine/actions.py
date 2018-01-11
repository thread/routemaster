"""Action (webhook invocation) evaluator."""

import json
import logging
from typing import Callable

from sqlalchemy import func

from routemaster.db import history
from routemaster.app import App
from routemaster.utils import suppress_exceptions
from routemaster.config import Action, StateMachine
from routemaster.webhooks import (
    WebhookResult,
    webhook_runner_for_state_machine,
)
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    lock_label,
    labels_in_state,
    choose_next_state,
    context_for_label,
    get_current_state,
    get_label_metadata,
    process_transitions,
)
from routemaster.state_machine.exceptions import DeletedLabel

logger = logging.getLogger(__name__)


def process_action(
    app: App,
    action: Action,
    state_machine: StateMachine,
    label: LabelRef,
    conn,
) -> bool:
    """
    Process an action for a label.

    Assumes that `action` is the current state of the label, and that the label
    has been locked.

    Returns whether the label progressed in the state machine, for which `True`
    implies further progression should be attempted.
    """

    metadata, deleted = get_label_metadata(label, state_machine, conn)
    if deleted:
        raise DeletedLabel(label)

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

    context = context_for_label(label, metadata, state_machine, action)
    next_state = choose_next_state(state_machine, action, context)

    conn.execute(history.insert().values(
        label_state_machine=state_machine.name,
        label_name=label.name,
        created=func.now(),
        old_state=action.name,
        new_state=next_state.name,
    ))

    return True


def process_retries(
    app: App,
    state_machine: StateMachine,
    action: Action,
    should_terminate: Callable[[], bool],
) -> None:
    """
    Cron retry entrypoint. This will retry all labels in a given action.
    """
    with app.db.begin() as conn:
        relevant_labels = labels_in_state(state_machine, action, conn)

    for label_name in relevant_labels:
        if should_terminate():
            break

        with suppress_exceptions(logger):
            label = LabelRef(name=label_name, state_machine=state_machine.name)
            could_progress = False

            with app.db.begin() as conn:
                lock_label(label, conn)
                current_state = get_current_state(label, state_machine, conn)

                if current_state != action:
                    continue

                could_progress = process_action(
                    app,
                    action,
                    state_machine,
                    label,
                    conn,
                )

            if could_progress:
                process_transitions(app, label)
