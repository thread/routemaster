"""The core of the state machine logic."""

from typing import Iterable

from sqlalchemy import and_, not_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.utils import dict_merge
from routemaster.config import Gate, State, Action, StateMachine
from routemaster.state_machine.gates import (
    process_gate,
    transactional_process_gate,
)
from routemaster.state_machine.types import LabelRef, Metadata
from routemaster.state_machine.utils import \
    get_label_metadata as get_label_metadata_internal
from routemaster.state_machine.utils import (
    lock_label,
    get_current_state,
    get_state_machine,
    start_state_machine,
    needs_gate_evaluation_for_metadata_change,
)
from routemaster.state_machine.actions import process_action
from routemaster.state_machine.exceptions import (
    DeletedLabel,
    UnknownLabel,
    LabelAlreadyExists,
)


def list_labels(app: App, state_machine: StateMachine) -> Iterable[LabelRef]:
    """
    Returns a sorted iterable of labels associated with a state machine.

    Labels are returned ordered alphabetically by name.
    """
    with app.db.begin() as conn:
        label_names = conn.execute(
            select([
                labels.c.name,
            ]).where(and_(
                labels.c.state_machine == state_machine.name,
                not_(labels.c.deleted),
            )).order_by(
                labels.c.name,
            ),
        )
        for row in label_names:
            yield LabelRef(row[labels.c.name], state_machine.name)


def get_label_state(app: App, label: LabelRef) -> State:
    """Finds the current state of a label."""
    state_machine = get_state_machine(app, label)

    with app.db.begin() as conn:
        return get_current_state(label, state_machine, conn)


def get_label_metadata(app: App, label: LabelRef) -> Metadata:
    """Returns the metadata associated with a label."""
    state_machine = get_state_machine(app, label)

    with app.db.begin() as conn:
        row = get_label_metadata_internal(label, state_machine, conn)

        if row is None:
            raise UnknownLabel(label)

        metadata, deleted = row
        if deleted:
            raise DeletedLabel(label)

        return metadata


def create_label(app: App, label: LabelRef, metadata: Metadata) -> Metadata:
    """Creates a label and starts it in a state machine."""
    state_machine = get_state_machine(app, label)

    with app.db.begin() as conn:
        try:
            conn.execute(labels.insert().values(
                name=label.name,
                state_machine=state_machine.name,
                metadata=metadata,
            ))
        except IntegrityError:
            raise LabelAlreadyExists(label)

        start_state_machine(app, label, conn)

    # Outside transaction
    _process_transitions(app, label)
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

    with app.db.begin() as conn:
        row = lock_label(label, conn)

        existing_metadata, deleted = row.metadata, row.deleted
        if deleted:
            raise DeletedLabel(label)

        needs_gate_evaluation = needs_gate_evaluation_for_metadata_change(
            state_machine,
            label,
            update,
            conn,
        )

        new_metadata = dict_merge(existing_metadata, update)

        conn.execute(labels.update().where(and_(
            labels.c.name == label.name,
            labels.c.state_machine == label.state_machine,
        )).values(
            metadata=new_metadata,
            metadata_triggers_processed=not needs_gate_evaluation,
        ))

    # Outside transaction
    if needs_gate_evaluation:
        try:
            could_progress = transactional_process_gate(app, label)
            if could_progress:
                _process_transitions(app, label)
        except Exception:
            # This is allowed to fail here. We have successfully saved the new
            # metadata, and it has a metadata_triggers_processed=False flag so
            # will be picked up again for processing later.
            pass

    return new_metadata


def _process_transitions(app: App, label: LabelRef):
    state_machine = get_state_machine(app, label)
    could_progress = True

    while could_progress:
        with app.db.begin() as conn:
            lock_label(label, conn)
            current_state = get_current_state(label, state_machine, conn)

            if isinstance(current_state, Action):
                could_progress = process_action(
                    app,
                    current_state,
                    label,
                    conn,
                )

            elif isinstance(current_state, Gate):  # pragma: no branch
                if not current_state.trigger_on_entry:
                    return

                could_progress = process_gate(
                    app,
                    current_state,
                    label,
                    conn,
                )

            else:
                raise RuntimeError(  # pragma: no cover
                    "Unsupported state type {0}".format(current_state),
                )


def delete_label(app: App, label: LabelRef) -> None:
    """
    Deletes the metadata for a label and marks the label as deleted.

    The history for the label is not changed (in order to allow post-hoc
    analysis of the path the label took through the state machine).
    """
    state_machine = get_state_machine(app, label)

    label_filter = and_(
        labels.c.name == label.name,
        labels.c.state_machine == state_machine.name,
    )

    with app.db.begin() as conn:
        existing_metadata = conn.scalar(
            select([labels.c.metadata]).where(label_filter),
        )
        if existing_metadata is None:
            return

        # Record the label as having been deleted and remove its metadata
        conn.execute(labels.update().where(label_filter).values(
            metadata={},
            deleted=True,
        ))

        # Add a history entry for the deletion
        current_state_name = conn.scalar(
            select([history.c.new_state]).where(and_(
                history.c.label_name == label.name,
                history.c.label_state_machine == label.state_machine,
            )).order_by(
                history.c.created.desc(),
            ).limit(1)
        )
        conn.execute(history.insert().values(
            label_name=label.name,
            label_state_machine=label.state_machine,
            old_state=current_state_name,
            new_state=None,
        ))
