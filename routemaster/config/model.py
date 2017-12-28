"""Loading and validation of config files."""

import datetime
from typing import Any, Dict, List, Union, Mapping, Iterable, NamedTuple

from routemaster.utils import get_path
from routemaster.exit_conditions import ExitConditionProgram


class TimeTrigger(NamedTuple):
    """Time based trigger for exit condition evaluation."""
    time: datetime.time


class IntervalTrigger(NamedTuple):
    """Time based trigger for exit condition evaluation."""
    interval: datetime.timedelta


class MetadataTrigger(NamedTuple):
    """Context update based trigger for exit condition evaluation."""
    metadata_path: str

    def should_trigger_for_update(self, update: Dict[str, Any]) -> bool:
        """Returns whether this trigger should fire for a given update."""
        def applies(path, d):
            if not path:
                return False
            component, path = path[0], path[1:]
            if component in d:
                if path:
                    return applies(path, d[component])
                return True
            return False
        return applies(self.metadata_path.split('.'), update)


Trigger = Union[TimeTrigger, IntervalTrigger, MetadataTrigger]


class ConstantNextState(NamedTuple):
    """Defines a constant choice, always chooses `state`."""
    state: str

    def next_state_for_label(self, label_context: Any) -> str:
        """Returns the constant next state."""
        return self.state

    def all_destinations(self) -> Iterable[str]:
        """Returns the constant next state."""
        return [self.state]


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
        val = get_path(self.path.split('.'), label_context)
        for destination in self.destinations:
            if destination.value == val:
                return destination.state
        raise RuntimeError("Handle this gracefully.")

    def all_destinations(self) -> Iterable[str]:
        """Returns all possible destination states."""
        return [x.state for x in self.destinations]


class NoNextStates(NamedTuple):
    """Represents the lack of a next state to progress to."""

    def next_state_for_label(self, label_context: Any) -> str:
        """Invalid to call, raise an exception."""
        raise RuntimeError(
            "Attempted to progress from a state with no next state",
        )

    def all_destinations(self) -> Iterable[str]:
        """Returns no states."""
        return []


NextStates = Union[ConstantNextState, ContextNextStates, NoNextStates]


class Gate(NamedTuple):
    """
    A state that restricts a label from moving based on an exit condition.

    Gates cannot perform an action.
    """
    name: str
    next_states: NextStates

    exit_condition: ExitConditionProgram
    triggers: Iterable[Trigger]

    @property
    def metadata_triggers(self) -> List[MetadataTrigger]:
        """Return a list of the metadata triggers for this state."""
        return [x for x in self.triggers if isinstance(x, MetadataTrigger)]


class Action(NamedTuple):
    """
    A state that performs an action via a webhook.

    A label staying in this state means that the action has not succeeded, i.e.
    the webhook returned an error status.
    """
    name: str
    next_states: NextStates

    webhook: str


State = Union[Action, Gate]


class StateMachine(NamedTuple):
    """A state machine."""
    name: str
    states: List[State]

    def get_state(self, state_name: str) -> State:
        """Get the state object for a given state name."""
        return [x for x in self.states if x.name == state_name][0]


class DatabaseConfig(NamedTuple):
    """Database connection configuration."""
    host: str
    port: int
    name: str
    username: str
    password: str

    @property
    def connstr(self) -> str:
        """Connection string for given configuration."""
        if not self.host:
            return f'postgresql:///{self.name}'

        auth = ''
        if self.username and not self.password:
            auth = f'{self.username}@'
        elif self.username and self.password:
            auth = f'{self.username}:{self.password}@'

        return f'postgresql://{auth}{self.host}/{self.name}'


class Config(NamedTuple):
    """
    The top-level configuration object.

    Stores the configured state machines, and other system-level configuration.
    """
    state_machines: Mapping[str, StateMachine]
    database: DatabaseConfig
