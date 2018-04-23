"""Processing for gate states."""
from sqlalchemy import func

from routemaster.db import Label, History
from routemaster.app import App
from routemaster.config import Gate, State, StateMachine
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    choose_next_state,
    context_for_label,
    get_state_machine,
    get_label_metadata,
    get_current_history,
)
from routemaster.state_machine.exceptions import DeletedLabel


def process_gate(
    *,
    app: App,
    state: State,
    state_machine: StateMachine,
    label: LabelRef,
) -> bool:
    """
    Process a label in a gate, continuing if necessary.

    Assumes that `gate` is the current state of the label, and that the label
    has been locked.

    Returns whether the label progressed in the state machine, for which `True`
    implies further progression should be attempted.
    """
    if not isinstance(state, Gate):  # pragma: no branch
        raise ValueError(  # pragma: no cover
            f"process_gate called with {state.name} which is not an Gate",
        )

    gate = state

    state_machine = get_state_machine(app, label)
    metadata, deleted = get_label_metadata(app, label, state_machine)
    if deleted:
        raise DeletedLabel(label)

    history_entry = get_current_history(app, label)

    context = context_for_label(
        label,
        metadata,
        state_machine,
        gate,
        history_entry,
        app.logger,
    )
    can_exit = gate.exit_condition.run(context)

    if not can_exit:
        return False

    destination = choose_next_state(state_machine, gate, context)

    app.session.add(History(
        label_state_machine=state_machine.name,
        label_name=label.name,
        created=func.now(),
        old_state=gate.name,
        new_state=destination.name,
    ))

    app.session.query(Label).filter_by(
        name=label.name,
        state_machine=label.state_machine,
    ).update({
        'metadata_triggers_processed': True,
    })

    return True
