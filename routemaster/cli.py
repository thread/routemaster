"""CLI handling for `routemaster`."""
import yaml
import click

from routemaster.app import App
from routemaster.config import load_config
from routemaster.server import server
from routemaster.middleware import wrap_application
from routemaster.record_states import record_state_machines
from routemaster.gunicorn_application import GunicornWSGIApplication


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
    config = load_config(yaml.load(config_file))
    ctx.obj = App(config)


@main.command()
@click.pass_context
def validate(ctx):
    """Entrypoint for validation of configuration files."""
    print("Validating")
    print(ctx.obj)


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
@click.pass_context
def serve(ctx, bind, debug):
    """Entrypoint for serving the Routemaster HTTP service."""
    app = ctx.obj

    server.config.app = app
    if debug:
        server.config['DEBUG'] = True

    with app.new_session():
        record_state_machines(app, app.config.state_machines.values())

    wrapped_server = wrap_application(app, server)

    instance = GunicornWSGIApplication(wrapped_server, bind=bind, debug=debug)
    instance.run()
