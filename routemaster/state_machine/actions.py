"""Action (webhook invocation) evaluator."""

import json
import hashlib

from sqlalchemy import func

from routemaster.db import history
from routemaster.app import App
from routemaster.utils import template_url
from routemaster.config import State, Action, StateMachine
from routemaster.webhooks import (
    WebhookResult,
    webhook_runner_for_state_machine,
)
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    choose_next_state,
    context_for_label,
    get_label_metadata,
    get_current_history,
)
from routemaster.state_machine.exceptions import DeletedLabel


def process_action(
    *,
    app: App,
    state: State,
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
    if not isinstance(state, Action):  # pragma: no branch
        raise ValueError(  # pragma: no cover
            f"process_action called with {state.name} which is not an Action",
        )

    action = state

    metadata, deleted = get_label_metadata(label, state_machine, conn)
    if deleted:
        raise DeletedLabel(label)

    latest_history = get_current_history(label, conn)

    webhook_data = json.dumps({
        'metadata': metadata,
        'label': label.name,
    }, sort_keys=True).encode('utf-8')

    run_webhook = webhook_runner_for_state_machine(state_machine)

    idempotency_token = _calculate_idempotency_token(label, latest_history)

    with app.logger.process_webhook(state_machine, state):
        result = run_webhook(
            template_url(action.webhook, state_machine.name, label.name),
            'application/json',
            webhook_data,
            idempotency_token,
            app.logger.webhook_response,
        )

    if result != WebhookResult.SUCCESS:
        return False

    context = context_for_label(
        label,
        metadata,
        state_machine,
        action,
        latest_history,
        app.logger,
    )
    next_state = choose_next_state(state_machine, action, context)

    conn.execute(history.insert().values(
        label_state_machine=state_machine.name,
        label_name=label.name,
        created=func.now(),
        old_state=action.name,
        new_state=next_state.name,
    ))

    return True


def _calculate_idempotency_token(label: LabelRef, latest_history) -> str:
    """
    We want to make sure that an action is only performed once.

    While we attempt to only deliver an action webhook once, we cannot
    guarantee this in all cases, so we call webhooks with an
    _idempotency token_. This token allows the receiver to record that it has
    performed the appropriate action, and should not perform it again.

    Idempotency tokens must represent precisely one logical call to a webhook
    in the design of the state machine. For example:

    - An action being retried _must_ use the same idempotency token, in case
      the original failure was a network issue, and the receiver did indeed
      process the action.
    - An action being triggered again in a state machine that loops _must_ use
      a different token, as loops are a supported use-case.

    The label passed to this function _must_ be locked for the current
    transaction.
    """
    return hashlib.sha256(str(latest_history.id).encode('ascii')).hexdigest()
