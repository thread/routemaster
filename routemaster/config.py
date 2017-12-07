"""Loading and validation of config files."""

import re
import datetime
from typing import (
    Any,
    Dict,
    List,
    Union,
    Mapping,
    Iterable,
    Optional,
    NamedTuple,
)

from routemaster.exit_conditions import ExitConditionProgram

Yaml = Dict[str, Any]
Path = List[str]


class TimeTrigger(NamedTuple):
    """Time based trigger for exit condition evaluation."""
    time: datetime.time


class ContextTrigger(NamedTuple):
    """Context update based trigger for exit condition evaluation."""
    context_path: str


Trigger = Union[TimeTrigger, ContextTrigger]


class ConstantNextState(NamedTuple):
    """Defines a constant choice, always chooses `state`."""
    state: str

    def next_state_for_label(self, label_context: Any) -> str:
        """Returns the constant next state."""
        return self.state


class ContextNextStatesOption(NamedTuple):
    """Represents an option for a context conditional next state."""
    state: str
    value: Any


class ContextNextStates(NamedTuple):
    """Defined a choice based on a path in the given `label_context`."""
    path: str
    destinations: Iterable[ContextNextStatesOption]

    def next_state_for_label(self, label_context: Any) -> str:
        """Returns next state based on context value at `self.path`."""
        val = label_context.get_path(self.path)
        for destination in self.destinations:
            if destination.value == val:
                return destination.state
        raise RuntimeError("Handle this gracefully.")


class NoNextStates(NamedTuple):
    """Represents the lack of a next state to progress to."""

    def next_state_for_label(self, label_context: Any) -> str:
        """Invalid to call, raise an exception."""
        raise RuntimeError(
            "Attempted to progress from a state with no next state",
        )


NextStates = Union[ConstantNextState, ContextNextStates, NoNextStates]


class Gate(NamedTuple):
    """
    A state that restricts a label from moving based on an exit condition.

    Gates cannot perform an action.
    """
    name: str
    next_states: Optional[NextStates]

    exit_condition: ExitConditionProgram
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
            ['state_machines', name],
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
    yaml_exit_condition = yaml_state['exit_condition']

    if yaml_exit_condition is True:
        str_exit_condition = 'true'
    elif yaml_exit_condition is False:
        str_exit_condition = 'false'
    else:
        str_exit_condition = str(yaml_exit_condition).strip()

    return Gate(
        name=yaml_state['gate'],
        exit_condition=ExitConditionProgram(str_exit_condition),
        triggers=[
            _load_trigger(path + ['triggers', str(idx)], yaml_trigger)
            for idx, yaml_trigger in enumerate(yaml_state.get('triggers', []))
        ],
        next_states=_load_next_states(path + ['next'], yaml_state.get('next')),
    )


def _load_trigger(path: Path, yaml_trigger: Yaml) -> Trigger:
    if 'time' in yaml_trigger and 'context' in yaml_trigger:
        raise ConfigError(
            f"Trigger at path {'.'.join(path)} cannot be both a time and a "
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
    format = '%Hh%Mm'
    try:
        dt = datetime.datetime.strptime(str(yaml_trigger['time']), format)
        trigger = dt.time()
    except ValueError:
        raise ConfigError(
            f"Time trigger '{yaml_trigger['time']}' at path {'.'.join(path)} "
            f"does not meet expected format: {format}.",
        ) from None
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
        return NoNextStates()

    if yaml_next_states['type'] == 'constant':
        return _load_constant_next_state(path, yaml_next_states)
    elif yaml_next_states['type'] == 'context':
        return _load_context_next_states(path, yaml_next_states)
    else:
        raise ConfigError(
            f"Next state config at path {'.'.join(path)} must be of type "
            f"'constant' or 'context'",
        ) from None


def _load_constant_next_state(
    path: Path,
    yaml_next_states: Yaml,
) -> NextStates:
    return ConstantNextState(state=yaml_next_states['state'])


def _load_context_next_states(
    path: Path,
    yaml_next_states: Yaml,
) -> NextStates:
    return ContextNextStates(
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
) -> ContextNextStatesOption:
    return ContextNextStatesOption(
        state=yaml_option['state'],
        value=yaml_option['value'],
    )
