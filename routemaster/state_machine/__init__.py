"""Public API for state machines."""

from routemaster.state_machine.api import (
    Label,
    list_labels,
    create_label,
    get_label_metadata,
    update_metadata_for_label,
)
from routemaster.state_machine.exceptions import (
    UnknownLabel,
    LabelAlreadyExists,
    UnknownStateMachine,
)

__all__ = (
    'Label',
    'list_labels',
    'create_label',
    'UnknownLabel',
    'get_label_metadata',
    'LabelAlreadyExists',
    'UnknownStateMachine',
    'update_metadata_for_label',
)
