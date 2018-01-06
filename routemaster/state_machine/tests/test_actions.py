from sqlalchemy import select

from routemaster.db import history
from routemaster.webhooks import WebhookResult
from routemaster.state_machine.actions import process_retries


def test_actions_are_run_and_states_advanced(app_config, create_label, mock_webhook):
    (state_machine,) = app_config.config.state_machines.values()

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        create_label('foo', state_machine.name, {'should_progress': True})

    # Now attepmt to process the retry of the action, succeeding.
    with mock_webhook(WebhookResult.SUCCESS) as webhook:
        process_retries(
            app_config,
            state_machine,
            state_machine.states[1],
        )

    webhook.assert_called_once_with(
        'http://localhost/hook',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
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
            ('start', 'perform_action'),
            ('perform_action', 'end'),
        ]


def test_actions_do_not_advance_state_on_fail(app_config, create_label, mock_webhook):
    (state_machine,) = app_config.config.state_machines.values()

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        create_label('foo', state_machine.name, {'should_progress': True})

    with mock_webhook(WebhookResult.FAIL) as webhook:
        process_retries(
            app_config,
            state_machine,
            state_machine.states[1],
        )

    webhook.assert_called_once_with(
        'http://localhost/hook',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
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
            ('start', 'perform_action'),
        ]
