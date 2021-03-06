import functools
from unittest import mock

import pytest

from routemaster.webhooks import WebhookResult
from routemaster.state_machine import process_cron
from routemaster.state_machine.utils import labels_in_state
from routemaster.state_machine.actions import process_action
from routemaster.state_machine.exceptions import DeletedLabel


def test_actions_are_run_and_states_advanced(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        create_label('foo', state_machine.name, {'should_progress': True})

    # Now attempt to process the retry of the action, succeeding.
    with mock_webhook(WebhookResult.SUCCESS) as webhook:
        process_cron(
            process_action,
            functools.partial(labels_in_state, app),
            app,
            state_machine,
            state_machine.states[1],
        )

    webhook.assert_called_once_with(
        'http://localhost/hook/test_machine/foo',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
        mock.ANY,
        mock.ANY,
    )

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])


def test_actions_do_not_advance_state_on_fail(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock_webhook(WebhookResult.FAIL):
        create_label('foo', state_machine.name, {'should_progress': True})

    with mock_webhook(WebhookResult.FAIL) as webhook:
        process_cron(
            process_action,
            functools.partial(labels_in_state, app),
            app,
            state_machine,
            state_machine.states[1],
        )

    webhook.assert_called_once_with(
        'http://localhost/hook/test_machine/foo',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
        mock.ANY,
        mock.ANY,
    )

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
    ])


def test_actions_do_not_advance_if_label_in_wrong_state(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']

    # Set should_progress=False so that the label will remain in start.
    label = create_label('foo', state_machine.name, {'should_progress': False})

    with mock_webhook(WebhookResult.SUCCESS) as webhook:
        process_cron(
            process_action,
            # Return our target label for processing even though it shouldn't
            # be here. Simulates changes to labels where we aren't expecting.
            lambda x, y: [label.name],
            app,
            state_machine,
            state_machine.states[1],
        )

    webhook.assert_not_called()
    assert_history([
        (None, 'start'),
    ])


def test_actions_retries_use_same_idempotency_token(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']

    expected = {'token': None}

    def persist_token(url, content_type, data, token, logger):
        expected['token'] = token
        return WebhookResult.FAIL

    # First get the label into the action state by failing the automatic
    # progression through the machine.
    with mock.patch(
        'routemaster.webhooks.RequestsWebhookRunner.__call__',
        side_effect=persist_token,
    ) as webhook:
        create_label('foo', state_machine.name, {'should_progress': True})

    assert expected['token'] is not None

    webhook.assert_called_once_with(
        'http://localhost/hook/test_machine/foo',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
        expected['token'],
        mock.ANY,
    )

    with mock_webhook(WebhookResult.FAIL) as webhook:
        process_cron(
            process_action,
            functools.partial(labels_in_state, app),
            app,
            state_machine,
            state_machine.states[1],
        )

    webhook.assert_called_once_with(
        'http://localhost/hook/test_machine/foo',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
        expected['token'],
        mock.ANY,
    )

    with mock_webhook(WebhookResult.SUCCESS) as webhook:
        process_cron(
            process_action,
            functools.partial(labels_in_state, app),
            app,
            state_machine,
            state_machine.states[1],
        )

    webhook.assert_called_once_with(
        'http://localhost/hook/test_machine/foo',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
        expected['token'],
        mock.ANY,
    )


def test_different_actions_use_different_idempotency_tokens(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']

    seen_tokens = set()

    def persist_token(url, content_type, data, token, logger):
        seen_tokens.add(token)
        return WebhookResult.SUCCESS

    with mock.patch(
        'routemaster.webhooks.RequestsWebhookRunner.__call__',
        side_effect=persist_token,
    ) as webhook:
        create_label('foo', state_machine.name, {'should_progress': True})
        create_label('bar', state_machine.name, {'should_progress': True})
        create_label('baz', state_machine.name, {'should_progress': True})

    assert len(seen_tokens) == 3

    webhook.assert_has_calls((
        mock.call(
            'http://localhost/hook/test_machine/foo',
            'application/json',
            b'{"label": "foo", "metadata": {"should_progress": true}}',
            mock.ANY,
            mock.ANY,
        ),
        mock.call(
            'http://localhost/hook/test_machine/bar',
            'application/json',
            b'{"label": "bar", "metadata": {"should_progress": true}}',
            mock.ANY,
            mock.ANY,
        ),
        mock.call(
            'http://localhost/hook/test_machine/baz',
            'application/json',
            b'{"label": "baz", "metadata": {"should_progress": true}}',
            mock.ANY,
            mock.ANY,
        ),
    ))


def test_action_retry_trigger_continues_as_far_as_possible(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']

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
            'routemaster.state_machine.api.process_transitions',
        ) as mock_process_transitions:
            process_cron(
                process_action,
                functools.partial(labels_in_state, app),
                app,
                state_machine,
                state_machine.states[1],
            )

    mock_process_transitions.assert_called_once_with(
        app,
        label,
    )

    webhook.assert_called_once_with(
        'http://localhost/hook/test_machine/foo',
        'application/json',
        b'{"label": "foo", "metadata": {"should_progress": true}}',
        mock.ANY,
        mock.ANY,
    )

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])


def test_process_action_does_not_work_for_deleted_label(app, create_deleted_label, assert_history):
    deleted_label = create_deleted_label('foo', 'test_machine')
    state_machine = app.config.state_machines['test_machine']
    action = state_machine.states[1]

    with pytest.raises(DeletedLabel):
        with app.new_session():
            process_action(
                app=app,
                state=action,
                state_machine=state_machine,
                label=deleted_label,
            )

    assert_history([
        (None, 'start'),
        ('start', None),
    ])


def test_process_action(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']
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
        with app.new_session():
            process_action(
                app=app,
                state=action,
                state_machine=state_machine,
                label=label,
            )

        webhook.assert_called_once()

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])


def test_process_action_leaves_label_in_action_if_webhook_fails(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']
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
        with app.new_session():
            process_action(
                app=app,
                state=action,
                state_machine=state_machine,
                label=label,
            )

        webhook.assert_called_once()

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
    ])


def test_process_action_fails_retry_works(app, create_label, mock_webhook, assert_history):
    state_machine = app.config.state_machines['test_machine']
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
        process_cron(
            process_action,
            functools.partial(labels_in_state, app),
            app,
            state_machine,
            action,
        )
        webhook.assert_called_once()

    assert_history([
        (None, 'start'),
        ('start', 'perform_action'),
        ('perform_action', 'end'),
    ])
