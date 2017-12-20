"""CLI handling for `routemaster`."""
import yaml
import click
import gunicorn.app.base

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
    server.config.app = ctx.obj

    class HackyWSGIApplication(gunicorn.app.base.BaseApplication):
        def __init__(self, app, *, bind, debug):
            self.application = app
            self.bind = bind
            self.debug = debug
            super().__init__()

        def load_config(self):
            self.cfg.set('bind', self.bind)
            self.cfg.set('workers', 1)

            if self.debug:
                self.cfg.set('reload', True)
                self.cfg.set('accesslog', '-')

        def load(self):
            return self.application

    instance = HackyWSGIApplication(server, bind=bind, debug=debug)
    instance.run()
