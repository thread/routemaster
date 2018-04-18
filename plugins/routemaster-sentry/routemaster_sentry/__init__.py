"""
Sentry logger for Routemaster.

This package provides a Routemaster logging plugin that interfaces to Raven,
Sentry's Python reporting package.

It adds per-request exception reporting to Flask for the API, and also wraps
the cron, webhook request, and feed request processes with Sentry reporting.
All wrapping re-raises exceptions, as Routemaster/Flask/the cron subsystem will
all handle exceptions appropriately.
"""
import contextlib

import pkg_resources
from raven import Client
from raven.contrib.flask import Sentry

from routemaster.logging import BaseLogger


class SentryLogger(BaseLogger):
    """Instruments Routemaster with Sentry."""

    def __init__(self, *args, dsn):
        try:
            version = pkg_resources.working_set.by_key['routemaster'].version
        except KeyError:
            version = 'dev'

        self.client = Client(
            dsn,
            release=version,
            sample_rate=0 if 'dev' in version else 1,
            include_paths=[
                'routemaster',
            ],
        )

        super().__init__(*args)

    def init_flask(self, flask_app):
        """Instrument Flask with Sentry."""
        Sentry(flask_app, client=self.client)

    @contextlib.contextmanager
    def process_cron(self, state_machine, state, fn_name):
        """Send cron exceptions to Sentry."""
        try:
            yield
        except Exception:
            self.client.captureException()
            raise

    @contextlib.contextmanager
    def process_webhook(self, state_machine, state):
        """Send webhook request exceptions to Sentry."""
        try:
            yield
        except Exception:
            self.client.captureException()
            raise

    @contextlib.contextmanager
    def process_feed(self, state_machine, state, feed_url):
        """Send feed request exceptions to Sentry."""
        try:
            yield
        except Exception:
            self.client.captureException()
            raise
