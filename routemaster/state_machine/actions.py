"""Action (webhook invocation) evaluator."""

import json

from sqlalchemy import and_, func, select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.config import Action, StateMachine
from routemaster.webhooks import WebhookResult, WebhookRunner
from routemaster.state_machine.api import choose_next_state


def run_action(
    app: App,
    state_machine: StateMachine,
    action: Action,
    run_webhook: WebhookRunner,
) -> None:
    """Run `action` for all outstanding users."""
    with app.db.begin() as conn:
        ranked_transitions = select((
            history.c.label_name,
            history.c.old_state,
            history.c.new_state,
            func.row_number().over(
                order_by=history.c.created.desc(),
                partition_by=history.c.label_name,
            ).label('rank'),
        )).where(
            history.c.label_state_machine == state_machine.name,
        ).alias('transitions')

        active_participants = select((
            ranked_transitions.c.label_name,
            labels.c.metadata,
        )).where(and_(
            ranked_transitions.c.new_state == action.name,
            ranked_transitions.c.rank == 1,
            ranked_transitions.c.label_name == labels.c.name,
            labels.c.state_machine == state_machine.name,
        ))

        relevant_labels = {
            x.label_name: x.metadata
            for x in conn.execute(active_participants)
        }

        new_transitions = []

        for label_name, metadata in relevant_labels.items():
            webhook_argument = json.dumps({
                'metadata': metadata,
                'label': label_name,
            }, sort_keys=True).encode('utf-8')
            result = run_webhook(
                action.webhook,
                'application/json',
                webhook_argument,
            )

            if result == WebhookResult.SUCCESS:
                next_state = choose_next_state(state_machine, action, metadata)
                new_transitions.append((label_name, next_state.name))

        if new_transitions:
            conn.execute(
                history.insert().values(
                    label_state_machine=state_machine.name,
                    created=func.now(),
                    old_state=action.name,
                ),
                [
                    {
                        'label_name': label,
                        'new_state': next_state_name,
                    }
                    for label, next_state_name in new_transitions
                ],
            )
