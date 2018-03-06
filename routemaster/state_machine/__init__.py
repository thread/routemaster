"""Public API for state machines."""

from routemaster.state_machine.api import (
    LabelRef,
    LabelStateProcessor,
    list_labels,
    create_label,
    delete_label,
    process_cron,
    get_label_state,
    get_label_metadata,
    update_metadata_for_label,
)
from routemaster.state_machine.gates import process_gate
from routemaster.state_machine.utils import (
    labels_in_state,
    labels_needing_metadata_update_retry_in_gate,
)
from routemaster.state_machine.actions import process_action
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
    'process_cron',
    'process_gate',
    'UnknownLabel',
    'IsExitingCheck',
    'process_action',
    'get_label_state',
    'labels_in_state',
    'get_label_metadata',
    'LabelAlreadyExists',
    'LabelStateProcessor',
    'UnknownStateMachine',
    'update_metadata_for_label',
    'labels_needing_metadata_update_retry_in_gate',
)
