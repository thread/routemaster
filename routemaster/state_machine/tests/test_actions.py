import hashlib

import mock
import pytest

from routemaster.webhooks import WebhookResult
from routemaster.state_machine.actions import process_action, process_retries
from routemaster.state_machine.exceptions import DeletedLabel


def test_actions_are_run_and_states_advanced(app_config, create_label, mock_webhook, assert_history):
    state_machine = app_config.config.state_machines['test_machine']

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        create_label('foo', state_machine.name, {'should_progress': True})

    # Now attempt to process the retry of the action, succeeding.
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
        mock.ANY,
    )

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])


def test_actions_do_not_advance_state_on_fail(app_config, create_label, mock_webhook, assert_history):
    state_machine = app_config.config.state_machines['test_machine']

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
        mock.ANY,
    )

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
    ])


def test_actions_retries_use_same_idempotency_token(app_config, create_label, mock_webhook, assert_history):
    state_machine = app_config.config.state_machines['test_machine']

    # Figure out what our idempotency token should be
    with app_config.db.begin() as conn:
        latest_id = conn.scalar(
            'select nextval(pg_get_serial_sequence(\'history\', \'id\'))',
        )

    # We generate an entry before the one that will be used for the token
    history_offset = 2
    expected_token = hashlib.sha256(
        f'foo:{str(latest_id + history_offset)}'.encode('ascii'),
    ).hexdigest()

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL) as webhook:
        create_label('foo', state_machine.name, {'should_progress': True})

    webhook.assert_called_once_with(
        'http://localhost/hook',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
        expected_token,
    )

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
        expected_token,
    )

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
        expected_token,
    )


def test_action_retry_trigger_continues_as_far_as_possible(app_config, create_label, mock_webhook, assert_history):
    state_machine = app_config.config.state_machines['test_machine']

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        label = create_label(
            'foo',
            state_machine.name,
            {'should_progress': True},
        )

    # Now attempt to process the retry of the action, succeeding.
    with mock_webhook(WebhookResult.SUCCESS) as webhook:
        with mock.patch(
            'routemaster.state_machine.actions.process_transitions',
        ) as mock_process_transitions:
            process_retries(
                app_config,
                state_machine,
                state_machine.states[1],
            )

    mock_process_transitions.assert_called_once_with(
        app_config,
        label,
    )

    webhook.assert_called_once_with(
        'http://localhost/hook',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
        mock.ANY,
    )

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])


def test_process_action_does_not_work_for_deleted_label(app_config, create_deleted_label, assert_history):
    deleted_label = create_deleted_label('foo', 'test_machine')
    state_machine = app_config.config.state_machines['test_machine']
    action = state_machine.states[1]

    with pytest.raises(DeletedLabel):
        with app_config.db.begin() as conn:
            process_action(app_config, action, deleted_label, conn)

    assert_history([
        (None, 'start'),
        ('start', None),
    ])


def test_process_action(app_config, create_label, mock_webhook, assert_history):
    state_machine = app_config.config.state_machines['test_machine']
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

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])


def test_process_action_leaves_label_in_action_if_webhook_fails(app_config, create_label, mock_webhook, assert_history):
    state_machine = app_config.config.state_machines['test_machine']
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

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
    ])


def test_process_action_fails_retry_works(app_config, create_label, mock_webhook, assert_history):
    state_machine = app_config.config.state_machines['test_machine']
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
    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
    ])

    # Now retry with succeeding webhook
    with mock_webhook(WebhookResult.SUCCESS) as webhook:
        process_retries(app_config, state_machine, action)
        webhook.assert_called_once()

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])
