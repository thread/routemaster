"""Public API for state machines."""

from routemaster.state_machine.api import (
    Label,
    list_labels,
    create_label,
    delete_label,
    get_label_state,
    choose_next_state,
    get_label_context,
    update_context_for_label,
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
    'delete_label',
    'UnknownLabel',
    'get_label_context',
    'get_label_state',
    'choose_next_state',
    'LabelAlreadyExists',
    'UnknownStateMachine',
    'update_context_for_label',
)
