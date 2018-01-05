"""Action invocation."""

import enum
from typing import Callable

import requests


@enum.unique
class WebhookResult(enum.Enum):
    """Possible results from invoking a webhook."""
    SUCCESS = 'success'
    RETRY = 'retry'
    FAIL = 'fail'


WebhookRunner = Callable[[str, str, bytes], WebhookResult]


class RequestsWebhookRunner(object):
    """Webhook runner which uses `requests` to actually hit webhooks."""

    def __init__(self) -> None:
        self.session = requests.Session()

    def __call__(
        self,
        url: str,
        content_type: str,
        data: bytes,
    ) -> WebhookResult:
        """Run a POST on the given webhook."""
        try:
            result = self.session.post(
                url,
                data=data,
                headers={'Content-Type': content_type},
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