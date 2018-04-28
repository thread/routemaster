"""
Prometheus metrics exporter for Routemaster.

This package provides a Routemaster logging plugin that interfaces to the
Python Prometheus API, to export monitoring metrics to Prometheus.
"""
import os
import shutil
import pathlib
import contextlib
from timeit import default_timer as timer

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    CollectorRegistry,
    generate_latest,
)
import prometheus_client.core
from prometheus_client.multiprocess import MultiProcessCollector

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
    'webhook_requests',
    "Webhook requests",
    ('state_machine', 'state', 'status_code'),
)

api_histogram = Histogram(
    'routemaster_api_request_duration_seconds',
    'Routemaster API request duration in seconds',
    ('method', 'endpoint', 'status'),
)

api_counter = Counter(
    'routemaster_api_request_total',
    'Total number of API requests',
    ('method', 'status'),
)


class PrometheusLogger(BaseLogger):
    """Instruments Routemaster with Prometheus."""

    def __init__(
        self,
        *args,
        path='/metrics',
    ):
        self.path = path
        metrics_path = os.environ.get('prometheus_multiproc_dir')

        if not metrics_path:
            raise ValueError(
                "PrometheusLogger requires the environment variable "
                "`prometheus_multiproc_dir` to be set to a writeable "
                "directory.",
            )

        pathlib.Path(metrics_path).mkdir(parents=True, exist_ok=True)
        _clear_directory(metrics_path)

        super().__init__(*args)

    def init_flask(self, flask_app):
        """Instrument Flask with Prometheus."""

        @flask_app.route(self.path)
        def get_metrics():
            registry = CollectorRegistry()
            MultiProcessCollector(registry)
            data = generate_latest(registry)
            response_headers = [
                ('Content-type', CONTENT_TYPE_LATEST),
                ('Content-Length', str(len(data))),
            ]
            return data, 200, response_headers

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

    def process_request_started(self, environ):
        """Start a timer."""
        environ['_PROMETHEUS_REQUEST_TIMER'] = timer()

    def process_request_finished(
        self,
        environ,
        *,
        status,
        headers,
        exc_info,
    ):
        """Log completed request metrics, given the timer we started."""
        total_time = max(timer() - environ['_PROMETHEUS_REQUEST_TIMER'], 0)
        path = environ.get('PATH_INFO', '')

        if path == self.path:
            return

        api_histogram.labels(
            method=environ.get('REQUEST_METHOD'),
            endpoint=path,
            status=status,
        ).observe(total_time)

        api_counter.labels(
            method=environ.get('REQUEST_METHOD'),
            status=status,
        ).inc()


def _clear_directory(path: pathlib.Path):
    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))
