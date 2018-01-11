"""Processing for gate states."""
import logging

from sqlalchemy import and_

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.config import Gate, StateMachine
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    choose_next_state,
    context_for_label,
    get_state_machine,
    get_label_metadata,
)
from routemaster.state_machine.exceptions import DeletedLabel

logger = logging.getLogger(__name__)


def process_gate(
    app: App,
    gate: Gate,
    state_machine: StateMachine,
    label: LabelRef,
    conn,
) -> bool:
    """
    Process a label in a gate, continuing if necessary.

    Assumes that `gate` is the current state of the label, and that the label
    has been locked.

    Returns whether the label progressed in the state machine, for which `True`
    implies further progression should be attempted.
    """

    state_machine = get_state_machine(app, label)
    metadata, deleted = get_label_metadata(label, state_machine, conn)
    if deleted:
        raise DeletedLabel(label)

    context = context_for_label(label, metadata, state_machine, gate)
    can_exit = gate.exit_condition.run(context)

    if not can_exit:
        return False

    destination = choose_next_state(state_machine, gate, context)

    conn.execute(history.insert().values(
        label_name=label.name,
        label_state_machine=state_machine.name,
        old_state=gate.name,
        new_state=destination.name,
    ))

    conn.execute(labels.update().where(and_(
        labels.c.name == label.name,
        labels.c.state_machine == label.state_machine,
    )).values(
        metadata_triggers_processed=True,
    ))

    return True
