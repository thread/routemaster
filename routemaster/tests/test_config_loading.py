import contextlib

import yaml
import pytest

from routemaster.config import (
    Gate,
    Config,
    ConfigError,
    NoNextStates,
    StateMachine,
    load_config,
)


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
                        exit_condition=None,
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


# TODO: test_raises_for_no_state_machines
# TODO: test_raises_for_time_and_context_trigger
# TODO: test_raises_for_neither_time_nor_context_trigger
# TODO: test_raises_for_invalid_time_format_in_trigger
# TODO: test_raises_for_invalid_path_format_in_trigger
# TODO: test_raises_for_invalid_next_states_type
