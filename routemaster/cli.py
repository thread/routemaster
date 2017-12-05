"""CLI handling for `routemaster`."""
import yaml

import click

from routemaster import config


@click.command()
@click.option(
    '-c',
    '--config-file',
    help="Path to the service config file.",
    type=click.File(encoding='utf-8'),
    required=True,
)
def main(config_file):
    """Main entrypoint for CLI handling."""
    print(config.load_config(yaml.load(config_file)))
