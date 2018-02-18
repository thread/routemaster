"""The core of the state machine logic."""

from typing import Any, Callable, Iterable

import dateutil.tz
from sqlalchemy import and_, not_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from routemaster.db import Label, History
from routemaster.app import App
from routemaster.utils import dict_merge, suppress_exceptions
from routemaster.config import Gate, State, StateMachine
from routemaster.state_machine.gates import process_gate
from routemaster.state_machine.types import LabelRef, Metadata
from routemaster.state_machine.utils import (
    lock_label,
    get_current_state,
    get_state_machine,
)
from routemaster.state_machine.utils import \
    get_label_metadata as get_label_metadata_internal
from routemaster.state_machine.utils import (
    start_state_machine,
    needs_gate_evaluation_for_metadata_change,
)
from routemaster.state_machine.exceptions import (
    DeletedLabel,
    UnknownLabel,
    LabelAlreadyExists,
)
from routemaster.state_machine.transitions import process_transitions


def list_labels(app: App, state_machine: StateMachine) -> Iterable[LabelRef]:
    """
    Returns a sorted iterable of labels associated with a state machine.

    Labels are returned ordered alphabetically by name.
    """
    for (name,) in app.session.query(Label.name).filter_by(
        state_machine=state_machine.name,
        deleted=False,
    ):
        yield LabelRef(name=name, state_machine=state_machine.name)


def get_label_state(app: App, label: LabelRef) -> State:
    """Finds the current state of a label."""
    state_machine = get_state_machine(app, label)

    with app.db.begin() as conn:
        return get_current_state(label, state_machine, conn)


def get_label_metadata(app: App, label: LabelRef) -> Metadata:
    """Returns the metadata associated with a label."""
    state_machine = get_state_machine(app, label)

    row = app.session.query(Label).filter_by(
        name=label.name,
        state_machine=label.state_machine,
    ).one_or_none()

    if row is None:
        raise UnknownLabel(label)

    if row.deleted:
        raise DeletedLabel(label)

    return row.metadata


def create_label(app: App, label: LabelRef, metadata: Metadata) -> Metadata:
    """Creates a label and starts it in a state machine."""
    state_machine = get_state_machine(app, label)

    if app.session.query(
        app.session.query(Label).filter_by(
            name=label.name,
            state_machine=label.state_machine,
        ).exists()
    ).scalar():
        raise LabelAlreadyExists(label)

    app.session.add(Label(
        name=label.name,
        state_machine=state_machine.name,
        metadata=metadata,
    ))
    app.session.flush()

    start_state_machine(app, state_machine, label)

    # TODO: Savepoint
    process_transitions(app, label)
    return metadata


def update_metadata_for_label(
    app: App,
    label: LabelRef,
    update: Metadata,
) -> Metadata:
    """
    Updates the metadata for a label.

    Moves the label through the state machine as appropriate.
    """
    state_machine = get_state_machine(app, label)
    needs_gate_evaluation = False

    row = lock_label(app, label)

    existing_metadata, deleted = row.metadata, row.deleted
    if deleted:
        raise DeletedLabel(label)

    needs_gate_evaluation, current_state = \
        needs_gate_evaluation_for_metadata_change(
            app,
            state_machine,
            label,
            update,
        )

    new_metadata = dict_merge(existing_metadata, update)

    row.metadata = new_metadata
    row.metadata_triggers_processed = not needs_gate_evaluation
    app.session.add(row)

    # TODO: savepoint
    # Try to move the label forward, but this is not a hard requirement as
    # the cron will come back around to progress the label later.
    if needs_gate_evaluation:
        try:
            _process_transitions_for_metadata_update(
                app,
                label,
                state_machine,
                current_state,
            )
        except Exception:
            # This is allowed to fail here. We have successfully saved the new
            # metadata, and it has a metadata_triggers_processed=False flag so
            # will be picked up again for processing later.
            pass

    return new_metadata


def _process_transitions_for_metadata_update(
    app: App,
    label: LabelRef,
    state_machine: StateMachine,
    state_pending_update: State,
):
    with app.db.begin() as conn:
        lock_label(app, label)
        current_state = get_current_state(label, state_machine, conn)

        if state_pending_update != current_state:
            # We have raced with another update, and are no longer in
            # the state for which we needed an update, so we should
            # stop.
            return

        if not isinstance(current_state, Gate):  # pragma: no branch
            # Cannot be hit because of the semantics of
            # `needs_gate_evaluation_for_metadata_change`. Here to
            # appease mypy.
            raise RuntimeError(  # pragma: no cover
                "Label not in a gate",
            )

        could_progress = process_gate(
            app=app,
            state=current_state,
            state_machine=state_machine,
            label=label,
            conn=conn,
        )

    if could_progress:
        process_transitions(app, label)


def delete_label(app: App, label: LabelRef) -> None:
    """
    Deletes the metadata for a label and marks the label as deleted.

    The history for the label is not changed (in order to allow post-hoc
    analysis of the path the label took through the state machine).
    """
    state_machine = get_state_machine(app, label)  # Raises UnknownStateMachine

    try:
        row = lock_label(app, label)
    except UnknownLabel:
        return

    if row is None or row.deleted:
        return

    # Record the label as having been deleted and remove its metadata
    row.metadata = {}
    row.deleted = True
    app.session.add(row)

    # Add a history entry for the deletion
    current_state = get_current_state(app, label, state_machine)
    app.session.add(History(
        label_name=label.name,
        label_state_machine=label.state_machine,
        old_state=current_state.name,
        new_state=None,
    ))


LabelStateProcessor = Callable[[App, State, StateMachine, LabelRef, Any], bool]


def process_cron(
    process: LabelStateProcessor,
    get_labels: Callable[[StateMachine, State, Any], Iterable[str]],
    app: App,
    state_machine: StateMachine,
    state: State,
):
    """
    Cron event entrypoint.
    """
    with app.db.begin() as conn:
        relevant_labels = get_labels(state_machine, state, conn)

    for label_name in relevant_labels:
        with suppress_exceptions(app.logger):
            label = LabelRef(name=label_name, state_machine=state_machine.name)
            could_progress = False

            with app.db.begin() as conn:
                lock_label(app, label)
                current_state = get_current_state(label, state_machine, conn)

                if current_state != state:
                    continue

                could_progress = process(  # type: ignore
                    app=app,
                    state=state,
                    state_machine=state_machine,
                    label=label,
                    conn=conn,
                )

            if could_progress:
                process_transitions(app, label)
