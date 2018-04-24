"""
Prometheus metrics exporter for Routemaster.

This package provides a Routemaster logging plugin that interfaces to the
Python Prometheus API, to export monitoring metrics to Prometheus.
"""
import contextlib

from prometheus_client import Counter
from prometheus_flask_exporter import PrometheusMetrics

from routemaster.logging import BaseLogger

exceptions = Counter(
    'exceptions',
    "Exceptions logged",
    ('type',),
)

cron_jobs_processed = Counter(
    'cron_jobs_processed',
    "Cron jobs processed",
    ('fn_name', 'state_machine', 'state'),
)

feed_requests = Counter(
    'feed_requests',
    "Feed requests",
    ('feed_url', 'state_machine', 'state', 'status_code'),
)

webhook_requests = Counter(
    'feed_requests',
    "Feed requests",
    ('state_machine', 'state', 'status_code'),
)


class PrometheusLogger(BaseLogger):
    """Instruments Routemaster with Prometheus."""

    def __init__(self, *args, path='/metrics'):
        self.path = path
        super().__init__(*args)

    def init_flask(self, flask_app):
        """Instrument Flask with Prometheus."""
        self.metrics = PrometheusMetrics(flask_app, path=self.path)

    @contextlib.contextmanager
    def process_cron(self, state_machine, state, fn_name):
        """Send cron exceptions to Prometheus."""
        with exceptions.labels(type='cron').count_exceptions():
            yield
            cron_jobs_processed.labels(
                fn_name=fn_name,
                state_machine=state_machine.name,
                state=state.name,
            ).inc()

    @contextlib.contextmanager
    def process_webhook(self, state_machine, state):
        """Send webhook request exceptions to Prometheus."""
        with exceptions.labels(type='webhook').count_exceptions():
            yield

    @contextlib.contextmanager
    def process_feed(self, state_machine, state, feed_url):
        """Send feed request exceptions to Prometheus."""
        with exceptions.labels(type='feed').count_exceptions():
            yield

    def feed_response(
        self,
        state_machine,
        state,
        feed_url,
        response,
    ):
        """Log feed response with status code to Prometheus."""
        feed_requests.labels(
            feed_url=feed_url,
            state_machine=state_machine.name,
            state=state.name,
            status_code=response.status_code,
        ).inc()

    def webhook_response(
        self,
        state_machine,
        state,
        response,
    ):
        """Log webhook response with status code to Prometheus."""
        webhook_requests.labels(
            state_machine=state_machine.name,
            state=state.name,
            status_code=response.status_code,
        ).inc()
