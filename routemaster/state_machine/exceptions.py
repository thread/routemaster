"""State machine exceptions."""


class UnknownLabel(ValueError):
    """Represents a label unknown in the given state machine."""


class UnknownStateMachine(ValueError):
    """Represents a state machine not in the system."""


class LabelAlreadyExists(ValueError):
    """Thrown when a label already exists in the state machine."""
