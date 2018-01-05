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
        status=status,
    )
    runner = RequestsWebhookRunner()
    result = runner('http://example.com', 'application/json', b'{}')
    assert result == WebhookResult.RETRY


@httpretty.activate
def test_requests_webhook_runner_handles_timeout_as_retry():
    def raise_retry():
        raise requests.ReadTimeout()
    httpretty.register_uri(
        httpretty.POST,
        'http://example.com/',
        status=410,
        body=raise_retry,
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
