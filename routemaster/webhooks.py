"""Webhook invocation."""

import enum
from typing import Any, Dict, Callable, Iterable, Optional
from urllib.parse import urlparse, urlunparse

import requests

from routemaster.config import Webhook, StateMachine


@enum.unique
class WebhookResult(enum.Enum):
    """Possible results from invoking a webhook."""
    SUCCESS = 'success'
    RETRY = 'retry'
    FAIL = 'fail'


ResponseLogger = Callable[[requests.Response], None]
WebhookRunner = Callable[[str, str, bytes, str, ResponseLogger], WebhookResult]


class RequestsWebhookRunner(object):
    """
    Webhook runner which uses `requests` to actually hit webhooks.

    Optionally takes a list of webhook configs to modify how requests are made.
    """

    def __init__(
        self,
        webhook_configs: Iterable[Webhook]=(),
        url_builder: Callable[[str, Optional[int]], str]=(lambda x, y: x),
    ) -> None:
        # Use a session so that we can take advantage of connection pooling in
        # `urllib3`.
        self.session = requests.Session()
        self.webhook_configs = webhook_configs
        self.url_builder = url_builder

    def __call__(
        self,
        url: str,
        content_type: str,
        data: bytes,
        idempotency_token: str,
        log_response: ResponseLogger = lambda x: None,
    ) -> WebhookResult:
        """Run a POST on the given webhook."""
        headers = {
            'Content-Type': content_type,
            'X-Idempotency-Token': idempotency_token,
        }
        headers.update(self._headers_for_url(url))

        try:
            result = self.session.post(
                self.url_builder(url, self._localport_for_url(url)),
                data=data,
                headers=headers,
                timeout=10,
            )
            log_response(result)
        except requests.exceptions.RequestException:
            return WebhookResult.RETRY

        if result.status_code == 410:
            return WebhookResult.FAIL
        elif 200 <= result.status_code < 300:
            return WebhookResult.SUCCESS
        else:
            return WebhookResult.RETRY

    def _headers_for_url(self, url: str) -> Dict[str, Any]:
        headers = {}
        for config in self.webhook_configs:
            if config.match.search(url):
                headers.update(config.headers)
        return headers

    def _localport_for_url(self, url: str) -> Optional[int]:
        for config in self.webhook_configs:
            if config.match.search(url):
                return config.localport
        return None


def _to_local_scheme_netloc(
    base_value: tuple,
    localport: Optional[int],
) -> tuple:
    if localport:
        return ('http', 'localhost:{0}'.format(localport))

    return base_value


def _to_local_url(url: str, localport: Optional[int]) -> str:
    parts = urlparse(url)
    mapped_url = _to_local_scheme_netloc(parts[:2], localport) + parts[2:6]
    return urlunparse(mapped_url)


def webhook_runner_for_state_machine(
    state_machine: StateMachine,
    only_use_localhost=False,
) -> WebhookRunner:
    """
    Create the webhook runner for a given state machine.

    Applies any state machine configuration to the runner.
    """
    if only_use_localhost:
        return RequestsWebhookRunner(state_machine.webhooks, _to_local_url)

    return RequestsWebhookRunner(state_machine.webhooks)
