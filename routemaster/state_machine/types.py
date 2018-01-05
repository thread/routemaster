"""Shared types for state machine execution."""

from typing import NamedTuple


class LabelRef(NamedTuple):
    """API representation of a label for the state machine."""
    name: str
    state_machine: str
