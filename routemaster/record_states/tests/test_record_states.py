from routemaster.record_states import record_state_machines
from routemaster.db import state_machines, states
from routemaster.config import StateMachine, Gate, NoNextStates
from routemaster.exit_conditions import ExitConditionProgram


def test_record_no_states_has_no_effect(app_config):
    record_state_machines(app_config, [])

    with app_config.db.begin() as conn:
        num_machines = conn.scalar(state_machines.count())

    assert num_machines == 0


def test_record_single_trivial_machine(app_config):
    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        )
    ])

    with app_config.db.begin() as conn:
        num_machines = conn.scalar(state_machines.count())
        assert num_machines == 1

        machine_definition = conn.execute(state_machines.select()).fetchone()
        assert machine_definition.name == 'machine'

        num_states = conn.scalar(states.count())
        assert num_states == 1


def test_delete_single_trivial_machine(app_config):
    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        )
    ])

    record_state_machines(app_config, [])

    with app_config.db.begin() as conn:
        num_machines = conn.scalar(state_machines.count())
        assert num_machines == 0
