from unittest.mock import Mock

import pytest
import httpretty
from sqlalchemy import select

from routemaster.db import history
from routemaster.config import Action
from routemaster.actions import (
    WebhookResult,
    RequestsWebhookRunner,
    run_action,
)


def test_actions_are_run_and_states_advanced(app_config, create_label):
    (state_machine,) = app_config.config.state_machines.values()

    state_machine.states[0] = Action(
        name=state_machine.states[0].name,
        webhook='about:blank',
        next_states=state_machine.states[0].next_states,
    )

    create_label('foo', state_machine.name, {'bar': 'bazz'})

    run_webhook = Mock(return_value=WebhookResult.SUCCESS)

    run_action(
        app_config,
        state_machine,
        state_machine.states[0],
        run_webhook,
    )

    run_webhook.assert_called_once_with(
        'about:blank',
        'application/json',
        b'{"context": {"bar": "bazz"}, "label": "foo"}',
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

    run_action(
        app_config,
        state_machine,
        state_machine.states[0],
        run_webhook,
    )

    run_webhook.assert_called_once_with(
        'about:blank',
        'application/json',
        b'{"context": {"bar": "bazz"}, "label": "foo"}',
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


@httpretty.activate
def test_requests_webhook_runner_handles_200_as_success():
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        body='{}',
        content_type='application/json',
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}')
    assert result == WebhookResult.SUCCESS


@httpretty.activate
def test_requests_webhook_runner_handles_204_as_success():
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        status=204,
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}')
    assert result == WebhookResult.SUCCESS


@httpretty.activate
def test_requests_webhook_runner_handles_410_as_failure():
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        status=410,
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}')
    assert result == WebhookResult.FAIL


@pytest.mark.parametrize('status', [401, 403, 404, 500, 502, 503, 504])
@httpretty.activate
def test_requests_webhook_runner_handles_other_failure_modes_as_retry(status):
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        status=404,
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}')
    assert result == WebhookResult.RETRY


@httpretty.activate
def test_requests_webhook_runner_passes_post_data_through():
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        body='{}',
        content_type='application/json',
    )
    runner = RequestsWebhookRunner()
    runner('http://example.com', 'application/test-data', b'\0\xff')
    last_request = httpretty.last_request()
    assert last_request.headers['Content-Type'] == 'application/test-data'
    assert last_request.body == b'\0\xff'
