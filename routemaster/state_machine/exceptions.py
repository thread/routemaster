"""State machine exceptions."""


class UnknownLabel(ValueError):
    """Represents a label unknown in the given state machine."""
    deleted = False


class DeletedLabel(UnknownLabel):
    """Represents a label deleted in the given state machine."""
    deleted = True


class UnknownStateMachine(ValueError):
    """Represents a state machine not in the system."""


class LabelAlreadyExists(ValueError):
    """Thrown when a label already exists in the state machine."""
