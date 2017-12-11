"""Loading and validation of config files."""

import datetime
from typing import Any, Union, Mapping, Iterable, Optional, NamedTuple

from routemaster.exit_conditions import ExitConditionProgram


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