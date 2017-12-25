from sqlalchemy import func, select

from routemaster.db import Edge, State, StateMachine
from routemaster.config import StateMachine as ConfigStateMachine
from routemaster.config import Gate, NoNextStates, ConstantNextState
from routemaster.record_states import record_state_machines
from routemaster.exit_conditions import ExitConditionProgram


def test_record_no_states_has_no_effect(app_config):
    record_state_machines(app_config, [])

    num_machines = app_config.session.query(StateMachine).count()
    assert num_machines == 0


def test_record_single_trivial_machine(app_config):
    record_state_machines(app_config, [
        ConfigStateMachine(
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

    machine_definition = app_config.session.query(StateMachine).one()
    assert machine_definition.name == 'machine'

    state_definition = app_config.session.query(State).one()
    assert state_definition.name == 'state'
    assert not state_definition.deprecated

    num_edges = app_config.session.query(Edge).count()
    assert num_edges == 0


def test_delete_single_trivial_machine(app_config):
    record_state_machines(app_config, [
        ConfigStateMachine(
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

    num_machines = app_config.session.query(StateMachine).count()
    assert num_machines == 0


def test_deprecate_state_in_state_machine(app_config):
    record_state_machines(app_config, [
        ConfigStateMachine(
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
        ConfigStateMachine(
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

    state_deprecations = dict(
        app_config.session.query(
            State.name,
            State.deprecated,
        ),
    )

    assert state_deprecations == {
        'state_old': True,
        'state_new': False,
    }


def test_undeprecate_state_in_state_machine(app_config):
    record_state_machines(app_config, [
        ConfigStateMachine(
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
        ConfigStateMachine(
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
        ConfigStateMachine(
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

    state_deprecations = dict(
        app_config.session.query(
            State.name,
            State.deprecated,
        ),
    )

    assert state_deprecations == {
        'state_old': False,
        'state_new': True,
    }


def test_record_edges(app_config):
    record_state_machines(app_config, [
        ConfigStateMachine(
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

    assert app_config.session.query(State).count() == 2
    edge_definition = app_config.session.query(Edge).one()
    assert edge_definition.from_state == 'state1'
    assert edge_definition.to_state == 'state2'
    assert not edge_definition.deprecated


def test_edges_are_deprecated_when_removed(app_config):
    record_state_machines(app_config, [
        ConfigStateMachine(
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
        ConfigStateMachine(
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

    edge_deprecations = {
        (x.from_state, x.to_state): x.deprecated
        for x in app_config.session.query(Edge)
    }

    assert edge_deprecations == {
        ('state1', 'state2'): True,
        ('state1', 'state3'): False,
    }


def test_edges_are_undeprecated_when_readded(app_config):
    record_state_machines(app_config, [
        ConfigStateMachine(
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
        ConfigStateMachine(
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
        ConfigStateMachine(
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

    edge_definition = app_config.session.query(Edge).one()
    assert not edge_definition.deprecated
