"""CLI handling for `routemaster`."""
import logging

import yaml
import click

from routemaster.app import App
from routemaster.cron import CronThread
from routemaster.config import ConfigError, load_config
from routemaster.server import server
from routemaster.middleware import wrap_application
from routemaster.validation import ValidationError, validate_config
from routemaster.gunicorn_application import GunicornWSGIApplication

logger = logging.getLogger(__name__)


@click.group()
@click.option(
    '-c',
    '--config-file',
    help="Path to the service config file.",
    type=click.File(encoding='utf-8'),
    required=True,
)
@click.pass_context
def main(ctx, config_file):
    """Shared entrypoint configuration."""
    logging.getLogger('schedule').setLevel(logging.CRITICAL)

    try:
        config = load_config(yaml.load(config_file))
    except ConfigError:
        logger.exception("Configuration Error")
        click.get_current_context().exit(1)

    ctx.obj = App(config)
    _validate_config(ctx.obj)


@main.command()
@click.pass_context
def validate(ctx):
    """
    Entrypoint for validation of configuration files.

    Validation is done by the main handler in order to cover all code paths,
    so this function is a stub so that `serve` does not have to be called.
    """
    pass


@main.command()
@click.option(
    '-b',
    '--bind',
    help="Bind address and port.",
    type=str,
    default='[::]:2017',
)
@click.option(
    '--debug/--no-debug',
    help="Enable debugging mode.",
    default=False,
)
@click.option(
    '--workers',
    help="Number of gunicorn workers to run.",
    type=int,
    default=1,
)
@click.pass_context
def serve(ctx, bind, debug, workers):  # pragma: no cover
    """Entrypoint for serving the Routemaster HTTP service."""
    app = ctx.obj

    server.config.app = app
    if debug:
        server.config['DEBUG'] = True

    app.logger.init_flask(server)

    cron_thread = CronThread(app)
    cron_thread.start()

    wrapped_server = wrap_application(app, server)

    try:
        instance = GunicornWSGIApplication(
            wrapped_server,
            bind=bind,
            debug=debug,
            workers=workers,
        )
        instance.run()
    finally:
        cron_thread.stop()


def _validate_config(app: App):
    try:
        validate_config(app, app.config)
    except ValidationError as e:
        msg = f"Validation Error: {e}"
        logger.exception(msg)
        click.get_current_context().exit(1)
