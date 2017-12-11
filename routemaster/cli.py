"""CLI handling for `routemaster`."""
import click

from routemaster import app
from routemaster.server import server


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
    app.load_config(config_file)


@main.command()
@click.pass_context
def validate(ctx):
    """Entrypoint for validation of configuration files."""
    print("Validating")
    print(app.config)


@main.command()
@click.option(
    '-h',
    '--host',
    help="Host for service.",
    type=str,
    default='127.0.0.1',
)
@click.option(
    '-p',
    '--port',
    help="Port for service.",
    type=int,
    default=2017,
)
@click.pass_context
def serve(ctx, host, port):
    """Entrypoint for serving the Routemaster HTTP service."""
    server.run(host=host, port=port)
