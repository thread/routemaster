import pytest

from routemaster.config import (
    Gate,
    NoNextStates,
    StateMachine,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
)
from routemaster.validation import ValidationError, _validate_state_machine
from routemaster.exit_conditions import ExitConditionProgram


def test_valid(app):
    _validate_state_machine(app, StateMachine(
        name='example',
        feeds=[],
        webhooks=[],
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
        ],
    ))


def test_disconnected_state_machine_invalid(app):
    state_machine = StateMachine(
        name='example',
        feeds=[],
        webhooks=[],
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
        ],
    )
    with pytest.raises(ValidationError):
        _validate_state_machine(app, state_machine)


def test_no_path_from_start_to_end_state_machine_invalid(app):
    state_machine = StateMachine(
        name='example',
        feeds=[],
        webhooks=[],
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

    with pytest.raises(ValidationError):
        _validate_state_machine(app, state_machine)


def test_nonexistent_node_destination_invalid(app):
    state_machine = StateMachine(
        name='example',
        feeds=[],
        webhooks=[],
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
                    ],
                    default='end',
                ),
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
    with pytest.raises(ValidationError):
        _validate_state_machine(app, state_machine)


def test_label_in_deleted_state_invalid(app, create_label):
    create_label('foo', 'test_machine', {})  # Created in "start" implicitly
    state_machine = StateMachine(
        name='test_machine',
        feeds=[],
        webhooks=[],
        states=[
            # Note: state "start" from "test_machine" is gone.
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ],
    )
    with pytest.raises(ValidationError):
        _validate_state_machine(app, state_machine)


def test_label_in_deleted_state_on_per_state_machine_basis(
    app,
    create_label,
):
    create_label('foo', 'test_machine', {})  # Created in "start" implicitly
    state_machine = StateMachine(
        name='other_machine',
        feeds=[],
        webhooks=[],
        states=[
            # Note: state "start" is not present, but that we're in a different
            # state machine.
            Gate(
                name='end',
                triggers=[],
                next_states=NoNextStates(),
                exit_condition=ExitConditionProgram('false'),
            ),
        ],
    )

    # Should not care about our label as it is in a different state machine.
    _validate_state_machine(app, state_machine)
