"""CLI handling for `routemaster`."""
import yaml
import click

from routemaster.app import App
from routemaster.config import load_config
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
    '-h',
    '--host',
    help="Host for service.",
    type=str,

    # Change to `::` once v6 is fixed in Sanic.
    # https://github.com/channelcat/sanic/pull/1053
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
    server.config.app = ctx.obj
    server.run(host=host, port=port)
