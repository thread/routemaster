"""State machine exceptions."""


class UnknownLabel(ValueError):
    """Represents a label unknown in the given state machine."""


class UnknownStateMachine(ValueError):
    """Represents a state machine not in the system."""
