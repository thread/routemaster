from routemaster.server import server


def test_propagate_exceptions_is_enabled():
    """
    Exception propagation is enabled in the Flask instance.

    This is required for middleware to be able to correctly process errors on
    500s (including, for instance, rolling back transactions).
    """
    # We check this at the config level, rather than the property, because
    # the property is always true in test mode.
    assert server.config['PROPAGATE_EXCEPTIONS'] is True
