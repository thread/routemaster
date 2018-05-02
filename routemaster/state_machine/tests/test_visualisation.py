from routemaster.state_machine import convert_to_network


def test_convert_to_network(app):
    convert_to_network(app.config.state_machines['test_machine'])
