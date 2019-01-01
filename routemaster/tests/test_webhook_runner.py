import pytest
import requests
import httpretty

from routemaster.webhooks import WebhookResult, RequestsWebhookRunner


@httpretty.activate
def test_requests_webhook_runner_handles_200_as_success():
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        body='{}',
        content_type='application/json',
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}', '')
    assert result == WebhookResult.SUCCESS


@httpretty.activate
def test_requests_webhook_runner_handles_204_as_success():
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        status=204,
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}', '')
    assert result == WebhookResult.SUCCESS


@httpretty.activate
def test_requests_webhook_runner_handles_410_as_failure():
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        status=410,
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}', '')
    assert result == WebhookResult.FAIL


@pytest.mark.parametrize('status', [401, 403, 404, 500, 502, 503, 504])
@httpretty.activate
def test_requests_webhook_runner_handles_other_failure_modes_as_retry(status):
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        status=status,
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}', '')
    assert result == WebhookResult.RETRY


@httpretty.activate
def test_requests_webhook_runner_handles_timeout_as_retry():
    def raise_retry(*args, **kwargs):
        raise requests.ReadTimeout()

    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        status=410,
        body=raise_retry,
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}', '')
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
    runner('http://example.com', 'application/test-data', b'\0\xff', '')
    last_request = httpretty.last_request()
    assert last_request.headers['Content-Type'] == 'application/test-data'
    assert last_request.body == b'\0\xff'


@httpretty.activate
def test_requests_webhook_runner_for_state_machine_uses_webhook_config(app):
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        body='{}',
        content_type='application/json',
    )

    state_machine = app.config.state_machines['test_machine']
    runner = app.get_webhook_runner(state_machine)
    runner('http://example.com', 'application/test-data', b'\0\xff', '')

    last_request = httpretty.last_request()
    assert last_request.headers['x-api-key'] == \
        'Rahfew7eed1ierae0moa2sho3ieB1et3ohhum0Ei'


@httpretty.activate
def test_requests_webhook_runner_for_state_machine_does_not_apply_headers_for_non_matching_url(app):
    httpretty.register_uri(
        httpretty.POST,
        'http://not-example.com/',
        body='{}',
        content_type='application/json',
    )

    state_machine = app.config.state_machines['test_machine']
    runner = app.get_webhook_runner(state_machine)
    runner('http://not-example.com', 'application/test-data', b'\0\xff', '')

    last_request = httpretty.last_request()
    assert last_request.headers['x-api-key'] is None


@httpretty.activate
def test_requests_webhook_runner_passes_idempotency_token_through():
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        body='{}',
        content_type='application/json',
    )
    token = 'foobar'
    runner = RequestsWebhookRunner()
    runner('http://example.com', 'application/test-data', b'\0\xff', token)
    last_request = httpretty.last_request()
    assert last_request.headers['X-Idempotency-Token'] == token
