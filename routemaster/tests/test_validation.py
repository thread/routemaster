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


async def test_valid(app_factory):
    await validate(app_factory(), StateMachine(
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


async def test_disconnected_state_machine_invalid(app_factory):
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
        await validate(app_factory(), state_machine)


async def test_nonexistent_node_destination_invalid(app_factory):
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
        await validate(app_factory(), state_machine)


async def test_label_in_deleted_state_invalid(app_factory, create_label):
    # TODO
    await create_label('foo', 'state_machine', {})
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
        await validate(app_factory(), state_machine)
