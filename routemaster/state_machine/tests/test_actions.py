from unittest.mock import Mock

from sqlalchemy import select

from routemaster.db import history
from routemaster.config import Action
from routemaster.webhooks import WebhookResult
from routemaster.state_machine.actions import process_retries


def test_actions_are_run_and_states_advanced(app_config, create_label):
    (state_machine,) = app_config.config.state_machines.values()

    state_machine.states[0] = Action(
        name=state_machine.states[0].name,
        webhook='about:blank',
        next_states=state_machine.states[0].next_states,
    )

    create_label('foo', state_machine.name, {'bar': 'bazz'})

    run_webhook = Mock(return_value=WebhookResult.SUCCESS)

    process_retries(
        app_config,
        state_machine,
        state_machine.states[0],
    )

    run_webhook.assert_called_once_with(
        'about:blank',
        'application/json',
        b'{"metadata": {"bar": "bazz"}, "label": "foo"}',
    )

    with app_config.db.begin() as conn:
        history_entries = [
            tuple(x)
            for x in conn.execute(
                select((
                    history.c.old_state,
                    history.c.new_state,
                )).order_by(history.c.id.asc()),
            )
        ]

        assert history_entries == [
            (None, 'start'),
            ('start', 'end'),
        ]


def test_actions_do_not_advance_state_on_fail(app_config, create_label):
    (state_machine,) = app_config.config.state_machines.values()

    state_machine.states[0] = Action(
        name=state_machine.states[0].name,
        webhook='about:blank',
        next_states=state_machine.states[0].next_states,
    )

    create_label('foo', state_machine.name, {'bar': 'bazz'})

    run_webhook = Mock(return_value=WebhookResult.FAIL)

    process_retries(
        app_config,
        state_machine,
        state_machine.states[0],
    )

    run_webhook.assert_called_once_with(
        'about:blank',
        'application/json',
        b'{"metadata": {"bar": "bazz"}, "label": "foo"}',
    )

    with app_config.db.begin() as conn:
        history_entries = [
            tuple(x)
            for x in conn.execute(
                select((
                    history.c.old_state,
                    history.c.new_state,
                )).order_by(history.c.id.asc()),
            )
        ]

        assert history_entries == [
            (None, 'start'),
        ]
