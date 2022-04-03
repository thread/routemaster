"""
Statsd metrics exporter for Routemaster.

This package provides a Routemaster logging plugin that pushes metrics to a
Statsd server.
"""
import os
import contextlib
from timeit import default_timer as timer

import statsd
from werkzeug.routing import NotFound, RequestRedirect, MethodNotAllowed

from routemaster.logging import BaseLogger

DEFAULT_HOST = os.environ.get('STATSD_HOST', 'localhost')
DEFAULT_PORT = int(os.environ.get('STATSD_PORT', 8125))


class StatsDLogger(BaseLogger):
    """Instruments Routemaster with Statsd."""

    def __init__(
        self,
        *args,
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        namespace='routemaster',
        tags=None,
    ):
        self.statsd = statsd.StatsdClient(
            host=host,
            port=int(port),
            namespace=namespace,
            tags=tags or {},
        )
        super().__init__(*args)

    def init_flask(self, flask_app):
        """Get routing information out of Flask."""
        self.url_adapter = flask_app.url_map.bind('localhost')
        self.endpoint_lookup = {
            rule.endpoint: rule.rule
            for rule in flask_app.url_map.iter_rules()
        }

    @contextlib.contextmanager
    def process_cron(self, state_machine, state, fn_name):
        """Send cron exceptions to Statsd."""
        try:
            yield
        except Exception:  # noqa: B902
            self.statsd.increment('exceptions', tags={'type': 'cron'})
            raise
        finally:
            self.statsd.increment('cron_jobs_processed', tags={
                'fn_name': fn_name,
                'state_machine': state_machine.name,
                'state': state.name,
            })

    @contextlib.contextmanager
    def process_webhook(self, state_machine, state):
        """Send webhook request exceptions to Statsd."""
        try:
            yield
        except Exception:  # noqa: B902
            self.statsd.increment('exceptions', tags={'type': 'webhook'})
            raise

    @contextlib.contextmanager
    def process_feed(self, state_machine, state, feed_url):
        """Send feed request exceptions to Statsd."""
        try:
            yield
        except Exception:  # noqa: B902
            self.statsd.increment('exceptions', tags={'type': 'feed'})
            raise

    def feed_response(
        self,
        state_machine,
        state,
        feed_url,
        response,
    ):
        """Log feed response with status code to Statsd."""
        self.statsd.increment('feed_requests', tags={
            'feed_url': feed_url,
            'state_machine': state_machine.name,
            'state': state.name,
            'status_code': str(response.status_code),
        })

    def webhook_response(
        self,
        state_machine,
        state,
        response,
    ):
        """Log webhook response with status code to Statsd."""
        self.statsd.increment('webhook_requests', tags={
            'state_machine': state_machine.name,
            'state': state.name,
            'status_code': str(response.status_code),
        })

    def process_request_started(self, environ):
        """Start a timer."""
        environ['_STATSD_REQUEST_TIMER'] = timer()

    def process_request_finished(
        self,
        environ,
        *,
        status,
        headers,
        exc_info,
    ):
        """Log completed request metrics, given the timer we started."""
        if exc_info:
            self.statsd.increment('exceptions', tags={'type': 'api'})

        total_time = max(
            int(1000 * (timer() - environ['_STATSD_REQUEST_TIMER'])),
            0,
        )
        path = environ['PATH_INFO']
        method = environ['REQUEST_METHOD']

        endpoint = ''

        try:
            match = self.url_adapter.match(path, method=method)
            if match:
                endpoint = self.endpoint_lookup[match[0]]
        except (RequestRedirect, MethodNotAllowed, NotFound):
            pass

        self.statsd.timing(
            'api_request_duration',
            total_time,
            tags={
                'method': method,
                'status': str(status),
                'endpoint': endpoint,
            },
        )
