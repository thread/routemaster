"""CLI handling for `routemaster`."""
import click


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
    print(config_file.read())
