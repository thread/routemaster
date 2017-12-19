from sqlalchemy import select, func

from routemaster.db import states, state_machines, edges
from routemaster.config import Gate, NoNextStates, ConstantNextState, StateMachine
from routemaster.record_states import record_state_machines
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

        state_definition = conn.execute(states.select()).fetchone()
        assert state_definition.name == 'state'
        assert not state_definition.deprecated

        num_edges = conn.scalar(edges.count())
        assert num_edges == 0


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


def test_undeprecate_state_in_state_machine(app_config):
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
            'state_old': False,
            'state_new': True,
        }


def test_record_edges(app_config):
    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state1',
                    exit_condition=ExitConditionProgram('true'),
                    next_states=ConstantNextState('state2'),
                    triggers=[],
                ),
                Gate(
                    name='state2',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        )
    ])

    with app_config.db.begin() as conn:
        num_states = conn.scalar(states.count())
        assert num_states == 2

        num_edges = conn.scalar(edges.count())
        assert num_edges == 1

        edge_definition = conn.execute(edges.select()).fetchone()
        assert edge_definition.from_state == 'state1'
        assert edge_definition.to_state == 'state2'
        assert not edge_definition.deprecated


def test_edges_are_deprecated_when_removed(app_config):
    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state1',
                    exit_condition=ExitConditionProgram('true'),
                    next_states=ConstantNextState('state2'),
                    triggers=[],
                ),
                Gate(
                    name='state2',
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
                    name='state1',
                    exit_condition=ExitConditionProgram('true'),
                    next_states=ConstantNextState('state3'),
                    triggers=[],
                ),
                Gate(
                    name='state3',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        )
    ])

    with app_config.db.begin() as conn:
        num_edges = conn.scalar(edges.count())
        assert num_edges == 2

        edge_deprecations = {
            (x.from_state, x.to_state): x.deprecated
            for x in conn.execute(
                select((
                    edges.c.from_state,
                    edges.c.to_state,
                    edges.c.deprecated,
                )).where(
                    edges.c.state_machine == 'machine'
                )
            )
        }
        assert edge_deprecations == {
            ('state1', 'state2'): True,
            ('state1', 'state3'): False,
        }


def test_edges_are_undeprecated_when_readded(app_config):
    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state1',
                    exit_condition=ExitConditionProgram('true'),
                    next_states=ConstantNextState('state2'),
                    triggers=[],
                ),
                Gate(
                    name='state2',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        ),
    ])

    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state1',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        ),
    ])

    record_state_machines(app_config, [
        StateMachine(
            name='machine',
            states=[
                Gate(
                    name='state1',
                    exit_condition=ExitConditionProgram('true'),
                    next_states=ConstantNextState('state2'),
                    triggers=[],
                ),
                Gate(
                    name='state2',
                    exit_condition=ExitConditionProgram('false'),
                    next_states=NoNextStates(),
                    triggers=[],
                ),
            ],
        ),
    ])

    with app_config.db.begin() as conn:
        num_edges = conn.scalar(edges.count())
        assert num_edges == 1

        any_deprecated = conn.scalar(
            select((
                func.bool_or(
                    edges.c.deprecated,
                ),
            )),
        )

        assert not any_deprecated
