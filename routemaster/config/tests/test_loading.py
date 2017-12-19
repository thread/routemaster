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
    MetadataTrigger,
    DatabaseConfig,
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
        },
        database=DatabaseConfig(
            host='localhost',
            port=5432,
            name='routemaster',
            username='',
            password='',
        ),
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
                            MetadataTrigger(metadata_path='foo.bar'),
                        ],
                        next_states=ConstantNextState(state='stage2'),
                        exit_condition=ExitConditionProgram('true'),
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
                        exit_condition=ExitConditionProgram('foo.bar is defined'),
                    ),
                    Action(
                        name='stage3',
                        webhook='https://localhost/hook',
                        next_states=ConstantNextState(state='end'),
                    ),
                    Gate(
                        name='end',
                        triggers=[],
                        exit_condition=ExitConditionProgram('false'),
                        next_states=NoNextStates(),
                    ),
                ],
            ),
        },
        database=DatabaseConfig(
            host='localhost',
            port=5432,
            name='routemaster_test',
            username='routemaster',
            password='routemaster',
        ),
    )
    assert load_config(data) == expected


def test_raises_for_action_and_gate_state():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('action_and_gate_invalid'))


def test_raises_for_neither_action_nor_gate_state():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('not_action_or_gate_invalid'))


def test_raises_for_no_state_machines():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('no_state_machines_invalid'))


def test_raises_for_time_and_context_trigger():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('time_and_context_invalid'))


def test_raises_for_neither_time_nor_context_trigger():
    with assert_config_error("Trigger at path state_machines.example.states.0.triggers.0 must be either a time or a metadata trigger."):
        load_config(yaml_data('not_time_or_context_invalid'))


def test_raises_for_invalid_time_format_in_trigger():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('trigger_time_format_invalid'))


def test_raises_for_invalid_path_format_in_trigger():
    with assert_config_error("Metadata trigger 'foo.bar+' at path state_machines.example.states.0.triggers.0 is not a valid dotted path."):
        load_config(yaml_data('path_format_context_trigger_invalid'))


def test_raises_for_neither_constant_no_context_next_states():
    with assert_config_error("Could not validate config file against schema."):
        load_config(yaml_data('next_states_not_constant_or_context_invalid'))
