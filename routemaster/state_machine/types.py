"""Shared types for state machine execution."""

from typing import Any, Dict, Callable, NamedTuple

from routemaster.app import App
from routemaster.config import State, StateMachine

Metadata = Dict[str, Any]
IsExitingCheck = Callable[[], bool]
StateProcessor = Callable[
    [App, State, StateMachine, IsExitingCheck],
    None,
]


class LabelRef(NamedTuple):
    """API representation of a label for the state machine."""
    name: str
    state_machine: str
