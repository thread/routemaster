"""Action invocation."""

import enum
from typing import Any, Dict, List, Callable

import requests

from routemaster.config import Webhook, StateMachine


@enum.unique
class WebhookResult(enum.Enum):
    """Possible results from invoking a webhook."""
    SUCCESS = 'success'
    RETRY = 'retry'
    FAIL = 'fail'


WebhookRunner = Callable[[str, str, bytes], WebhookResult]


class RequestsWebhookRunner(object):
    """
    Webhook runner which uses `requests` to actually hit webhooks.

    Optionally takes a list of webhook configs to modify how requests are made.
    """

    def __init__(self, webhook_configs: List[Webhook]=[]) -> None:
        self.session = requests.Session()
        self.webhook_configs = webhook_configs

    def __call__(
        self,
        url: str,
        content_type: str,
        data: bytes,
    ) -> WebhookResult:
        """Run a POST on the given webhook."""
        headers = {'Content-Type': content_type}
        headers.update(self._headers_for_url(url))

        try:
            result = self.session.post(
                url,
                data=data,
                headers=headers,
                timeout=10,
            )
        except requests.exceptions.RequestException:
            return WebhookResult.RETRY

        if result.status_code == 410:
            return WebhookResult.FAIL
        elif str(result.status_code)[0] == '2':
            return WebhookResult.SUCCESS
        else:
            return WebhookResult.RETRY

    def _headers_for_url(self, url: str) -> Dict[str, Any]:
        headers = {}
        for config in self.webhook_configs:
            if config.match.search(url):
                print("matched!", config.headers)
                headers.update(config.headers)
            else:
                print("did not match", config.match, url)
        return headers


def webhook_runner_for_state_machine(
    state_machine: StateMachine,
) -> WebhookRunner:
    """
    Create the webhook runner for a given state machine.

    Applies any state machine configuration to the runner.
    """
    return RequestsWebhookRunner(state_machine.webhooks)
