import pytest

from routemaster.webhooks import WebhookResult
from routemaster.state_machine.actions import process_action, process_retries
from routemaster.state_machine.exceptions import DeletedLabel


def test_actions_are_run_and_states_advanced(app_config, create_label, mock_webhook, assert_history):
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

    assert_history(app_config, [
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])


def test_actions_do_not_advance_state_on_fail(app_config, create_label, mock_webhook, assert_history):
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

    assert_history(app_config, [
        (None, 'start'),
        ('start', 'perform_action'),
    ])


def test_process_action_does_not_work_for_deleted_label(app_config, create_deleted_label, assert_history):
    deleted_label = create_deleted_label('foo', 'test_machine')
    (state_machine,) = app_config.config.state_machines.values()
    action = state_machine.states[1]

    with pytest.raises(DeletedLabel):
        with app_config.db.begin() as conn:
            process_action(app_config, action, deleted_label, conn)

    assert_history(app_config, [
        (None, 'start'),
        ('start', None),
    ])


def test_process_action(app_config, create_label, mock_webhook, assert_history):
    (state_machine,) = app_config.config.state_machines.values()
    action = state_machine.states[1]

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        label = create_label(
            'foo',
            state_machine.name,
            {'should_progress': True},
        )

    with mock_webhook(WebhookResult.SUCCESS) as webhook:
        with app_config.db.begin() as conn:
            process_action(app_config, action, label, conn)

        webhook.assert_called_once()

    assert_history(app_config, [
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])


def test_process_action_leaves_label_in_action_if_webhook_fails(app_config, create_label, mock_webhook, assert_history):
    (state_machine,) = app_config.config.state_machines.values()
    action = state_machine.states[1]

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        label = create_label(
            'foo',
            state_machine.name,
            {'should_progress': True},
        )

    with mock_webhook(WebhookResult.FAIL) as webhook:
        with app_config.db.begin() as conn:
            process_action(app_config, action, label, conn)

        webhook.assert_called_once()

    assert_history(app_config, [
        (None, 'start'),
        ('start', 'perform_action'),
    ])


def test_process_action_fails_retry_works(app_config, create_label, mock_webhook, assert_history):
    (state_machine,) = app_config.config.state_machines.values()
    action = state_machine.states[1]

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        create_label(
            'foo',
            state_machine.name,
            {'should_progress': True},
        )

    # State machine should not have progressed
    assert_history(app_config, [
        (None, 'start'),
        ('start', 'perform_action'),
    ])

    # Now retry with succeeding webhook
    with mock_webhook(WebhookResult.SUCCESS) as webhook:
        process_retries(app_config, state_machine, action)
        webhook.assert_called_once()

    assert_history(app_config, [
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])
