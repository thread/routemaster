from routemaster.state_machine import draw_state_machine


def test_draw_state_machine(app_config):
    draw_state_machine(app_config.config.state_machines['test_machine'])
