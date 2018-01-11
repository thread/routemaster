"""Processing for gate states."""
import logging
from typing import Callable

from sqlalchemy import and_

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.utils import suppress_exceptions
from routemaster.config import Gate, StateMachine
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    lock_label,
    labels_in_state,
    choose_next_state,
    context_for_label,
    get_current_state,
    get_state_machine,
    get_label_metadata,
    process_transitions,
    labels_needing_metadata_update_retry_in_gate,
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


def process_trigger(
    app: App,
    state_machine: StateMachine,
    gate: Gate,
    should_terminate: Callable[[], bool],
) -> None:
    """
    Cron trigger entrypoint. This will evaluate all labels in a given gate.
    """
    with app.db.begin() as conn:
        relevant_labels = labels_in_state(state_machine, gate, conn)

    for label_name in relevant_labels:
        if should_terminate():
            break

        with suppress_exceptions(logger):
            label = LabelRef(name=label_name, state_machine=state_machine.name)
            could_progress = False

            with app.db.begin() as conn:
                lock_label(label, conn)
                current_state = get_current_state(label, state_machine, conn)

                if current_state != gate:
                    continue

                could_progress = process_gate(
                    app,
                    gate,
                    state_machine,
                    label,
                    conn,
                )

            if could_progress:
                process_transitions(app, label)


def process_metadata_retries(
    app: App,
    state_machine: StateMachine,
    gate: Gate,
    should_terminate: Callable[[], bool],
) -> None:
    """
    Cron metadata retry entrypoint.

    This will re-evaluate all labels in a given gate that have
    `metadata_triggers_processed` set to False
    """
    with app.db.begin() as conn:
        relevant_labels = labels_needing_metadata_update_retry_in_gate(
            state_machine,
            gate,
            conn,
        )

    for label_name in relevant_labels:
        if should_terminate():
            break

        with suppress_exceptions(logger):
            label = LabelRef(name=label_name, state_machine=state_machine.name)
            could_progress = False

            with app.db.begin() as conn:
                lock_label(label, conn)
                current_state = get_current_state(label, state_machine, conn)

                if current_state != gate:
                    continue

                could_progress = process_gate(
                    app,
                    gate,
                    state_machine,
                    label,
                    conn,
                )

            if could_progress:
                process_transitions(app, label)
