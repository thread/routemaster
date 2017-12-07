import datetime
import contextlib

import yaml
import pytest

from routemaster.config import (
    Gate,
    Action,
    Config,
    ConfigError,
    TimeTrigger,
    NoNextStates,
    StateMachine,
    ContextTrigger,
    ConstantNextState,
    ContextNextStates,
    ContextNextStatesOption,
    load_config,
)
from routemaster.exit_conditions import ExitConditionProgram


def yaml_data(name: str):
    with open(f'test_data/{name}.yaml') as f:
        return yaml.load(f)


@contextlib.contextmanager
def assert_config_error(message: str):
    with pytest.raises(ConfigError) as excinfo:
        yield
    assert str(excinfo.value) == message


def test_trivial_config():
    data = yaml_data('trivial')
    expected = Config(
        state_machines={
            'example': StateMachine(
                name='example',
                states=[
                    Gate(
                        name='start',
                        triggers=[],
                        next_states=NoNextStates(),
                        exit_condition=ExitConditionProgram('false'),
                    ),
                ]
            )
        }
    )
    assert load_config(data) == expected


def test_realistic_config():
    data = yaml_data('realistic')
    expected = Config(
        state_machines={
            'example': StateMachine(
                name='example',
                states=[
                    Gate(
                        name='start',
                        triggers=[
                            TimeTrigger(time=datetime.time(18, 30)),
                            ContextTrigger(context_path='foo.bar'),
                        ],
                        next_states=ConstantNextState(state='stage2'),
                        exit_condition=None,
                    ),
                    Gate(
                        name='stage2',
                        triggers=[],
                        next_states=ContextNextStates(
                            path='foo.bar',
                            destinations=[
                                ContextNextStatesOption(state='stage3', value='1'),
                                ContextNextStatesOption(state='stage3', value='2'),
                            ]
                        ),
                        exit_condition=None,
                    ),
                    Action(
                        name='stage3',
                        webhook='https://localhost/hook',
                        next_states=ConstantNextState(state='end'),
                    ),
                    Gate(
                        name='end',
                        triggers=[],
                        exit_condition=None,
                        next_states=NoNextStates(),
                    ),
                ]
            )
        }
    )
    assert load_config(data) == expected


def test_raises_for_action_and_gate_state():
    with assert_config_error("State at path state_machines.example.0 cannot be both a gate and an action."):
        load_config(yaml_data('action_and_gate_invalid'))


def test_raises_for_neither_action_nor_gate_state():
    with assert_config_error("State at path state_machines.example.0 must be either a gate or an action."):
        load_config(yaml_data('not_action_or_gate_invalid'))


def test_raises_for_no_state_machines():
    with assert_config_error("No top-level state_machines key defined."):
        load_config(yaml_data('no_state_machines_invalid'))


def test_raises_for_time_and_context_trigger():
    with assert_config_error("Trigger at path state_machines.example.0.triggers.0 cannot be both a time and a context trigger."):
        load_config(yaml_data('time_and_context_invalid'))


def test_raises_for_neither_time_nor_context_trigger():
    with assert_config_error("Trigger at path state_machines.example.0.triggers.0 must be either a time or a context trigger."):
        load_config(yaml_data('not_time_or_context_invalid'))


def test_raises_for_invalid_time_format_in_trigger():
    with assert_config_error("Time trigger '1800' at path state_machines.example.0.triggers.0 does not meet expected format: %Hh%Mm."):
        load_config(yaml_data('trigger_time_format_invalid'))


def test_raises_for_invalid_path_format_in_trigger():
    with assert_config_error("Context trigger 'foo.bar+' at path state_machines.example.0.triggers.0 is not a valid dotted path."):
        load_config(yaml_data('path_format_context_trigger_invalid'))


def test_raises_for_neither_constant_no_context_next_states():
    with assert_config_error("Next state config at path state_machines.example.0.next must be of type 'constant' or 'context'"):
        load_config(yaml_data('next_states_not_constant_or_context_invalid'))
