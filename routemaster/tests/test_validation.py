from pathlib import Path

import yaml
import pytest

from routemaster.config import (
    Gate,
    NoNextStates,
    StateMachine,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
    load_config,
)
from routemaster.validation import (
    ValidationError,
    validate_config,
    _validate_state_machine,
)
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


def test_example_config_is_valid(app):
    """
    Test that the example.yaml in this repo is valid.

    This ensures that the example file itself is valid and is not intended as a
    test of the system.
    """

    repo_root = Path(__file__).parent.parent.parent
    example_yaml = repo_root / 'example.yaml'

    assert example_yaml.exists(), "Example file is missing! (is this test set up correctly?)"

    example_config = load_config(yaml.load(example_yaml.read_text()))

    # quick check that we've loaded the config we expect
    assert list(example_config.state_machines.keys()) == ['user_lifecycle']

    validate_config(app, example_config)
