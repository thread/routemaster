"""Action (webhook invocation) evaluator."""

import enum
import json
from typing import Callable

from sqlalchemy import and_, func, select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.config import Action, StateMachine
from routemaster.state_machine import choose_next_state


@enum.unique
class WebhookResult(enum.Enum):
    """Possible results from invoking a webhook."""
    SUCCESS = 'success'
    RETRY = 'retry'
    FAIL = 'fail'


def run_action(
    app: App,
    state_machine: StateMachine,
    action: Action,
    run_webhook: Callable[[str, bytes], WebhookResult],
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
            labels.c.context,
        )).where(and_(
            ranked_transitions.c.new_state == action.name,
            ranked_transitions.c.rank == 1,
            ranked_transitions.c.label_name == labels.c.name,
            labels.c.state_machine == state_machine.name,
        ))

        relevant_labels = {
            x.label_name: x.context
            for x in conn.execute(active_participants)
        }

        new_transitions = []

        for label_name, context in relevant_labels.items():
            webhook_argument = json.dumps({
                'context': context,
                'label': label_name,
            }, sort_keys=True).encode('utf-8')
            result = run_webhook(action.webhook, webhook_argument)

            if result == WebhookResult.SUCCESS:
                next_state = choose_next_state(state_machine, action, context)
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
