"""Processing for gate states."""

from sqlalchemy import and_

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.config import Gate
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    _lock_label,
    _choose_next_state,
    _context_for_label,
    _get_current_state,
    _get_state_machine,
    _get_label_metadata,
)
from routemaster.state_machine.exceptions import DeletedLabel


def transactional_process_gate(app: App, label: LabelRef) -> bool:
    """
    Process a label in a gate, continuing if necessary, in transactions.

    Transactional wrapper with required locking, around `process_gate`.

    Raises a TypeError when the current state is not a gate.
    """
    state_machine = _get_state_machine(app, label)

    with app.db.begin() as conn:
        _lock_label(label, conn)
        current_state = _get_current_state(label, state_machine, conn)
        if not isinstance(current_state, Gate):
            raise TypeError("Label not in a gate")
        return process_gate(app, current_state, label, conn)


def process_gate(app: App, gate: Gate, label: LabelRef, conn) -> bool:
    """
    Process a label in a gate, continuing if necessary.

    Assumes that `gate` is the current state of the label, and that the label
    has been locked.

    Returns whether the label progressed in the state machine, for which `True`
    implies further progression should be attempted.
    """

    state_machine = _get_state_machine(app, label)
    metadata, deleted = _get_label_metadata(label, state_machine, conn)
    if deleted:
        raise DeletedLabel(label)

    context = _context_for_label(label, metadata, state_machine, gate)
    can_exit = gate.exit_condition.run(context)

    if not can_exit:
        return False

    destination = _choose_next_state(state_machine, gate, context)

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
