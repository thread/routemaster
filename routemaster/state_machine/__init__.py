"""Public API for state machines."""

from routemaster.state_machine.api import (
    LabelRef,
    list_labels,
    create_label,
    delete_label,
    get_label_state,
    get_label_metadata,
    process_gate_trigger,
    process_action_retries,
    update_metadata_for_label,
    process_gate_metadata_retries,
)
from routemaster.state_machine.types import IsExitingCheck, StateProcessor
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
    'IsExitingCheck',
    'StateProcessor',
    'get_label_state',
    'get_label_metadata',
    'LabelAlreadyExists',
    'UnknownStateMachine',
    'process_gate_trigger',
    'process_action_retries',
    'update_metadata_for_label',
    'process_gate_metadata_retries',
)
