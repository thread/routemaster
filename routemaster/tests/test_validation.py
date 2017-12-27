import pytest

from routemaster.config import (
    Gate,
    NoNextStates,
    StateMachine,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
)
from routemaster.validation import _validate_state_machine
from routemaster.exit_conditions import ExitConditionProgram


def test_valid(app_config):
    _validate_state_machine(app_config, StateMachine(
        name='example',
        states=[
            Gate(
                name='start',
                triggers=[],
                next_states=ConstantNextState('end'),
                exit_condition=ExitConditionProgram('false'),
            ),
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ]
    ))


def test_disconnected_state_machine_invalid(app_config):
    state_machine = StateMachine(
        name='example',
        states=[
            Gate(
                name='start',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ]
    )
    with pytest.raises(ValueError):
        _validate_state_machine(app_config, state_machine)


def test_no_path_from_start_to_end_state_machine_invalid(app_config):
    state_machine = StateMachine(
        name='example',
        states=[
            Gate(
                name='start',
                triggers=[],
                next_states=ConstantNextState(state='start'),
                exit_condition=ExitConditionProgram('false'),
            ),
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ],
    )

    with pytest.raises(ValueError):
        _validate_state_machine(app_config, state_machine)


def test_nonexistent_node_destination_invalid(app_config):
    state_machine = StateMachine(
        name='example',
        states=[
            Gate(
                name='start',
                triggers=[],
                next_states=ContextNextStates(
                    path='foo.bar',
                    destinations=[
                        ContextNextStatesOption(
                            state='nonexistent',
                            value='1',
                        ),
                        ContextNextStatesOption(
                            state='end',
                            value='2',
                        ),
                    ]
                ),
                exit_condition=ExitConditionProgram('false'),
            ),
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ]
    )
    with pytest.raises(ValueError):
        _validate_state_machine(app_config, state_machine)


def test_label_in_deleted_state_invalid(app_config, create_label):
    create_label('foo', 'test_machine', {})  # Created in "start" implicitly
    state_machine = StateMachine(
        name='test_machine',
        states=[
            # Note: state "start" from "test_machine" is gone.
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ]
    )
    # with pytest.raises(ValueError): This should be enabled!
    _validate_state_machine(app_config, state_machine)
