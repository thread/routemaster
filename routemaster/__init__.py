"""A state machine service."""

from routemaster.app import App


def initialise():
    """Initialise the global app singleton."""
    global app
    app = App()


initialise()
