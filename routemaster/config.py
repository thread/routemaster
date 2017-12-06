"""Loading and validation of config files."""

import re
import abc
import time
from typing import (
    Any,
    Dict,
    List,
    Union,
    Mapping,
    Iterable,
    Optional,
    NamedTuple
)

Yaml = Dict[str, Any]
Path = List[str]


class TimeTrigger(NamedTuple):
    """Time based trigger for exit condition evaluation."""
    time: time.struct_time


class ContextTrigger(NamedTuple):
    """Context update based trigger for exit condition evaluation."""
    context_path: str


Trigger = Union[TimeTrigger, ContextTrigger]


class NextStates(NamedTuple):
    """Represents logic for how to continue from a state."""

    def next_state_for_label(self, label_context: Any) -> str:
        """
        Returns the name of the state that a given label should move to next.
        """

        raise NotImplementedError()


class ConstantNextState(NextStates):
    """Defines a constant choice, always chooses `next_state`."""
    next_state: str

    def next_state_for_label(self, label_context: Any) -> str:
        """Returns the constant next state."""
        return self.next_state


class ContextNextStateOption(NamedTuple):
    """Represents an option for a context conditional next state."""
    state: str
    value: Any


class ContextNextState(NextStates):
    """Defined a choice based on a path in the given `label_context`."""
    path: str
    destinations: Iterable[ContextNextStateOption]

    def next_state_for_label(self, label_context: Any) -> str:
        """Returns next state based on context value at `self.path`."""
        val = label_context.get_path(self.path)
        for destination in self.destinations:
            if destination.value == val:
                return destination.state
        raise RuntimeError("Handle this gracefully.")


class Gate(NamedTuple):
    """
    A state that restricts a label from moving based on an exit condition.

    Gates cannot perform an action.
    """
    name: str
    next_states: Optional[NextStates]

    exit_condition: Any
    triggers: Iterable[Trigger]


class Action(NamedTuple):
    """
    A state that performs an action via a webhook.

    A label staying in this state means that the action has not succeeded, i.e.
    the webhook returned an error status.
    """
    name: str
    next_states: Optional[NextStates]

    webhook: str


State = Union[Action, Gate]


class StateMachine(NamedTuple):
    """A state machine."""
    name: str
    states: Iterable[State]


class Config(NamedTuple):
    """
    The top-level configuration object.

    Stores the configured state machines, and other system-level configuration.
    """
    state_machines: Mapping[str, StateMachine]


class ConfigError(ValueError):
    """Represents an error validating the configuration file."""


def load_config(yaml: Yaml) -> Config:
    """Unpack a parsed YAML file into a `Config` object."""

    try:
        yaml_state_machines = yaml['state_machines']
    except KeyError:
        raise ConfigError("No top-level state_machines key defined.") from None

    return Config(state_machines={
        name: _load_state_machine(
            ['state_machine', name],
            name,
            yaml_state_machine,
        )
        for name, yaml_state_machine in yaml_state_machines.items()
    })


def _load_state_machine(
    path: Path,
    name: str,
    yaml_state_machine: Iterable[Yaml],
) -> StateMachine:
    return StateMachine(
        name=name,
        states=[
            _load_state(path + [str(idx)], yaml_state)
            for idx, yaml_state in enumerate(yaml_state_machine)
        ],
    )


def _load_state(path: Path, yaml_state: Yaml) -> State:
    if 'action' in yaml_state and 'gate' in yaml_state:
        raise ConfigError(
            f"State at path {'.'.join(path)} cannot be both a gate and an "
            f"action.",
        )

    if 'action' in yaml_state:
        return _load_action(path, yaml_state)
    elif 'gate' in yaml_state:
        return _load_gate(path, yaml_state)
    else:
        raise ConfigError(
            f"State at path {'.'.join(path)} must be either a gate or an "
            f"action.",
        )


def _load_action(path: Path, yaml_state: Yaml) -> Action:
    return Action(
        name=yaml_state['action'],
        webhook=yaml_state['webhook'],
        next_states=_load_next_states(
            path + ['next'],
            yaml_state.get('next'),
        ),
    )


def _load_gate(path: Path, yaml_state: Yaml) -> Gate:
    return Gate(
        name=yaml_state['gate'],
        exit_condition=None,
        triggers=[
            _load_trigger(path + ['triggers', str(idx)], yaml_trigger)
            for idx, yaml_trigger in enumerate(yaml_state.get('triggers', []))
        ],
        next_states=_load_next_states(path + ['next'], yaml_state.get('next')),
    )


def _load_trigger(path: Path, yaml_trigger: Yaml) -> Trigger:
    if 'time' in yaml_trigger and 'context' in yaml_trigger:
        raise ConfigError(
            f"Trigger at path {'.'.join('path')} cannot be both a time and a "
            f"context trigger."
        )

    if 'time' in yaml_trigger:
        return _load_time_trigger(path, yaml_trigger)
    elif 'context' in yaml_trigger:
        return _load_context_trigger(path, yaml_trigger)
    else:
        raise ConfigError(
            f"Trigger at path {'.'.join(path)} must be either a time or a "
            f"context trigger.",
        )


def _load_time_trigger(path: Path, yaml_trigger: Yaml) -> TimeTrigger:
    try:
        trigger = time.strptime(yaml_trigger['time'], '%H:%M')
    except ValueError:
        raise ConfigError(
            f"Time trigger '{yaml_trigger['time']}' at path {'.'.join(path)} "
            f"does not meet expected format: %H:%M.",
        )
    return TimeTrigger(time=trigger)


RE_PATH = re.compile(r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$')


def _load_context_trigger(path: Path, yaml_trigger: Yaml) -> ContextTrigger:
    context_path = yaml_trigger['context']
    if not RE_PATH.match(context_path):
        raise ConfigError(
            f"Context trigger '{context_path}' at path {'.'.join(path)} is "
            f"not a valid dotted path.",
        )
    return ContextTrigger(context_path=context_path)


def _load_next_states(
    path: Path,
    yaml_next_states: Optional[Yaml],
) -> NextStates:

    if yaml_next_states is None:
        return None

    try:
        return {
            'constant': _load_constant_next_state,
            'context': _load_context_next_states,
        }[yaml_next_states['type']](path, yaml_next_states)
    except KeyError:
        raise ConfigError(
            f"Next state config at path {'.'.join(path)} must be of type "
            f"'constant' or 'context'",
        ) from None


def _load_constant_next_state(
    path: Path,
    yaml_next_states: Yaml,
) -> ConstantNextState:
    return ConstantNextState(next_state=yaml_next_states['destination'])


def _load_context_next_states(
    path: Path,
    yaml_next_states: Yaml,
) -> ContextNextState:
    return ContextNextState(
        path=yaml_next_states['path'],
        destinations=[
            _load_context_next_state_option(
                path + ['destinations', str(idx)],
                yaml_option,
            )
            for idx, yaml_option in enumerate(yaml_next_states['destinations'])
        ],
    )


def _load_context_next_state_option(
    path: Path,
    yaml_option: Yaml,
) -> ContextNextStateOption:
    return ContextNextStateOption(
        state=yaml_option['state'],
        value=yaml_option['value'],
    )
