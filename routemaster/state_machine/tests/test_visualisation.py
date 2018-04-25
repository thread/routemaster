from routemaster.state_machine import convert_to_network


def test_convert_to_network(app_config):
    convert_to_network(app_config.config.state_machines['test_machine'])
