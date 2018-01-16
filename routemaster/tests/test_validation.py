import pytest

from routemaster.config import (
    Gate,
    Config,
    NoNextStates,
    StateMachine,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
)
from routemaster.validation import (
    ValidationError,
    _validate_state_machine,
    _validate_no_deleted_state_machines,
)
from routemaster.record_states import record_state_machines
from routemaster.exit_conditions import ExitConditionProgram


def test_valid(app_config):
    _validate_state_machine(app_config, StateMachine(
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
        ]
    ))


def test_disconnected_state_machine_invalid(app_config):
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
        ]
    )
    with pytest.raises(ValidationError):
        _validate_state_machine(app_config, state_machine)


def test_no_path_from_start_to_end_state_machine_invalid(app_config):
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
        _validate_state_machine(app_config, state_machine)


def test_nonexistent_node_destination_invalid(app_config):
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
        ]
    )
    with pytest.raises(ValidationError):
        _validate_state_machine(app_config, state_machine)


def test_label_in_deleted_state_invalid(app_config, create_label):
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
        ]
    )
    with pytest.raises(ValidationError):
        _validate_state_machine(app_config, state_machine)


def test_label_in_deleted_state_on_per_state_machine_basis(
    app_config,
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
        ]
    )
    with pytest.raises(ValidationError):
        _validate_state_machine(app_config, state_machine)


def test_deleted_state_machine_invalid(app_config):
    record_state_machines(app_config, [
        StateMachine(
            name='machine_1',
            feeds=[],
            webhooks=[],
            states=[
                Gate(
                    name='start',
                    triggers=[],
                    next_states=NoNextStates(),
                    exit_condition=ExitConditionProgram('false'),
                ),
            ]
        )
    ])

    state_machine = Config(
        state_machines={
            'machine_2': StateMachine(
                name='machine_2',
                feeds=[],
                webhooks=[],
                states=[
                    Gate(
                        name='start',
                        triggers=[],
                        next_states=NoNextStates(),
                        exit_condition=ExitConditionProgram('false'),
                    ),
                ]
            )
        },
        database=None,
    )
    with pytest.raises(ValidationError):
        _validate_no_deleted_state_machines(app_config, state_machine)
