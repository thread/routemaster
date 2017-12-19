from routemaster.record_states import record_state_machines
from routemaster.db import state_machines, states
from routemaster.config import StateMachine, Gate, NoNextStates
from routemaster.exit_conditions import ExitConditionProgram

from sqlalchemy import select


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

        state_definition = conn.execute(states.select()).fetchone()
        assert state_definition.name == 'state'
        assert not state_definition.deprecated


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


def test_deprecate_state_in_state_machine(app_config):
    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state_old',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        )
    ])

    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state_new',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        )
    ])

    with app_config.db.begin() as conn:
        state_deprecations = {
            x.name: x.deprecated
            for x in conn.execute(
                select((
                    states.c.name,
                    states.c.deprecated,
                )),
            )
        }

        assert state_deprecations == {
            'state_old': True,
            'state_new': False,
        }
