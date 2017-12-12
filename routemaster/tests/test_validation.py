import pytest

from routemaster.config import (
    Gate,
    NoNextStates,
    StateMachine,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
)
from routemaster.validation import validate
from routemaster.exit_conditions import ExitConditionProgram


def test_valid():
    validate(StateMachine(
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


def test_disconnected_state_machine_invalid():
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
        validate(state_machine)


def test_disconnected_state_machine_invalid():
    state_machine = StateMachine(
        name='example',
        states=[
            Gate(
                name='start',
                triggers=[],
                next_states=ContextNextStates(
                    path='foo.bar',
                    destinations=[
                        ContextNextStatesOption(state='nonexistent', value='1'),
                        ContextNextStatesOption(state='end', value='2'),
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
        validate(state_machine)