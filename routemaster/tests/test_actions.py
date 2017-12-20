from routemaster.actions import run_action


def test_basic_actions(app_config, create_label):
    (state_machine,) = app_config.config.state_machines.values()

    create_label('foo', state_machine.name, {'bar': 'bazz'})

    run_action(
        app_config,
        state_machine,
        state_machine.states[0],
    )
