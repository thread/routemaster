"""Processing of transitions between states."""

import textwrap

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

# The maximum transitions that may happen in a single `process_transitions`.
# Note that later transitions above this number will still happen, but after
# yielding to other cron processes, etc.
MAX_TRANSITIONS = 50


def process_transitions(app: App, label: LabelRef) -> None:
    """
    Process each transition for a label until it cannot move any further.

    Will silently accept DeletedLabel exceptions and end the processing of
    transitions.
    """

    state_machine = get_state_machine(app, label)
    could_progress = True
    num_transitions = 0

    def _transition() -> bool:
        with app.db.begin() as conn:
            lock_label(label, conn)
            current_state = get_current_state(label, state_machine, conn)

            if isinstance(current_state, Action):
                return process_action(
                    app=app,
                    state=current_state,
                    state_machine=state_machine,
                    label=label,
                    conn=conn,
                )

            elif isinstance(current_state, Gate):  # pragma: no branch
                if not current_state.trigger_on_entry:
                    return False

                return process_gate(
                    app=app,
                    state=current_state,
                    state_machine=state_machine,
                    label=label,
                    conn=conn,
                )

            else:
                raise RuntimeError(  # pragma: no cover
                    "Unsupported state type {0}".format(current_state),
                )

    while could_progress and num_transitions < MAX_TRANSITIONS:
        num_transitions += 1

        if num_transitions == MAX_TRANSITIONS:
            app.logger.warn(textwrap.dedent(
                f"""
                Label {label}
                hit the maximum number of transitions allowed in one go. This
                may indicate a bug, or could be negatively impacting your
                Routemaster cron processing. If it's not a bug, try using gates
                with time based exit conditions to break up the processing, or
                submit an issue or pull request to
                https://github.com/thread/routemaster with your use-case.
                """,
            ))

        try:
            could_progress = _transition()
        except DeletedLabel:
            # Label might have been deleted, that's a supported use-case,
            # not even a warning, and we should allow the this process to
            # continue.
            return
