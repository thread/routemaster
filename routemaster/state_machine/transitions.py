"""Processing of transitions between states."""

from routemaster.app import App
from routemaster.config import Gate, Action
from routemaster.state_machine.gates import process_gate
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    lock_label,
    get_current_state,
    get_state_machine,
)
from routemaster.state_machine.actions import process_action
from routemaster.state_machine.exceptions import DeletedLabel


def process_transitions(app: App, label: LabelRef) -> None:
    """
    Process each transition for a label until it cannot move any further.

    Will silently accept DeletedLabel exceptions and end the processing of
    transitions.
    """

    state_machine = get_state_machine(app, label)
    could_progress = True

    def _transition() -> bool:
        with app.db.begin() as conn:
            lock_label(label, conn)
            current_state = get_current_state(label, state_machine, conn)

            if isinstance(current_state, Action):
                return process_action(
                    app,
                    current_state,
                    state_machine,
                    label,
                    conn,
                )

            elif isinstance(current_state, Gate):  # pragma: no branch
                if not current_state.trigger_on_entry:
                    return False

                return process_gate(
                    app,
                    current_state,
                    state_machine,
                    label,
                    conn,
                )

            else:
                raise RuntimeError(  # pragma: no cover
                    "Unsupported state type {0}".format(current_state),
                )

    while could_progress:
        try:
            could_progress = _transition()
        except DeletedLabel:
            # Label might have been deleted, that's a supported use-case,
            # not even a warning, and we should allow the this process to
            # continue.
            pass
