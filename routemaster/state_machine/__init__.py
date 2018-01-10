"""Public API for state machines."""

from routemaster.state_machine.api import (
    LabelRef,
    list_labels,
    create_label,
    delete_label,
    get_label_state,
    get_label_metadata,
    update_metadata_for_label,
)
from routemaster.state_machine.actions import \
    process_retries as process_action_retries
from routemaster.state_machine.exceptions import (
    UnknownLabel,
    LabelAlreadyExists,
    UnknownStateMachine,
)

__all__ = (
    'LabelRef',
    'list_labels',
    'create_label',
    'delete_label',
    'UnknownLabel',
    'get_label_state',
    'get_label_metadata',
    'LabelAlreadyExists',
    'UnknownStateMachine',
    'process_action_retries',
    'update_metadata_for_label',
)
