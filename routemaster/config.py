"""Loading and validation of config files."""
import abc
import time

from typing import Any, Dict, List, Mapping, Iterable


Yaml = Dict[str, Any]
Path = List[str]


class TimeTrigger(Trigger):
    def __init__(self, time: time.Time):
        pass


class ContextTrigger(Trigger):
    def __init__(self, context_path: str):
        pass


Trigger = Union[TimeTrigger, ContextTrigger]


class State(metaclass=abc.ABCMeta):
    def __init__(self, *, name: str, next_states: Any) -> None:
        self.name = name
        self.next_states = next_states


class Gate(State):
    def __init__(
        self, *,
        name: str,
        next_states: Any,
        triggers: Iterable[Trigger],
        exit_condition: Any,
    ) -> None:
        """"""
        self.exit_condition = exit_condition
        super().__init__(name=name, next_states=next_states)


class Action(State):
    def __init__(self, *, name: str, next_states: Any, webhook: str) -> None:
        self.webhook = webhook
        super().__init__(name=name, next_states=next_states)


class StateMachine(object):
    def __init__(self, states: Iterable[State]) -> None:
        self.states = list(states)


class Config(object):
    def __init__(self, state_machines: Mapping[str, StateMachine]) -> None:
        self.state_machines = dict(state_machines)


class ConfigError(ValueError):
    pass


def load_config(yaml: Yaml) -> Config:
    try:
        yaml_state_machines = yaml['state_machines']
    except KeyError:
        raise ConfigError("No top-level state_machines key defined.") from None

    return Config(state_machines={
        name: load_state_machine(['state_machine', name], yaml_state_machine)
        for name, yaml_state_machine in yaml_state_machines.items()
    })


def load_state_machine(
    path: Path,
    yaml_state_machine: Iterable[Yaml],
) -> StateMachine:
    """TODO"""
    return StateMachine(states=[
        load_state(path + [str(idx)], yaml_state)
        for idx, yaml_state in enumerate(yaml_state_machine)
    ])


def load_state(path: Path, yaml_state: Yaml) -> State:
    if 'action' in yaml_state and 'gate' in yaml_state:
        raise ConfigError(
            f"State at path {'.'.join(path)} cannot be both a gate and an "
            f"action",
        )

    if 'action' in yaml_state:
        return load_action(path, yaml_state)
    elif 'gate' in yaml_state:
        return load_gate(path, yaml_state)
    else:
        raise ConfigError(
            f"State at path {'.'.join(path)} must be either a gate or an "
            f"action",
        )


def load_action(path: Path, yaml_state: Yaml) -> Action:
    return Action(
        name=yaml_state['action'],
        webhook=yaml_state['webhook'],
        next_states=load_next_states(path + ['next'], yaml_state['next']),
    )


def load_gate(path: Path, yaml_state: Yaml) -> Gate:
    return Gate(
        name=yaml_state['gate'],
        exit_condition=None,
        triggers=load_triggers(path + ['triggers'], yaml_state['triggers']),
        next_states=load_next_states(path + ['next'], yaml_state['next']),
    )


def load_triggers(path: Path, yaml: Yaml) -> Foo:
    pass


def load_next_states(path: Path, yaml: Yaml) -> Foo:
    pass

