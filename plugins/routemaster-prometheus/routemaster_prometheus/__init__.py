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

    @contextlib.contextmanager
    def process_request(self):
        """Send API request exceptions to Prometheus."""
        with exceptions.labels(type='request').count_exceptions():
            yield
