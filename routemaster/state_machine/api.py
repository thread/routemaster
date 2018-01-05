"""The core of the state machine logic."""

from typing import Any, Dict, Iterable

from sqlalchemy import and_, not_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.feeds import feeds_for_state_machine
from routemaster.utils import dict_merge
from routemaster.config import State, Action, StateMachine
from routemaster.context import Context
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.utils import (
    _utcnow,
    _get_state_machine,
    _start_state_machine,
)
from routemaster.state_machine.exceptions import (
    DeletedLabel,
    UnknownLabel,
    LabelAlreadyExists,
)

Metadata = Dict[str, Any]


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
    state_machine = _get_state_machine(app, label)

    with app.db.begin() as conn:
        history_entry = conn.execute(
            select([history]).where(and_(
                history.c.label_name == label.name,
                history.c.label_state_machine == state_machine.name,
            )).order_by(
                history.c.created.desc(),
            ).limit(1)
        ).fetchone()

    if history_entry is None:
        raise UnknownLabel(label)

    current_state = state_machine.get_state(history_entry.new_state)

    return current_state


def get_label_metadata(app: App, label: LabelRef) -> Metadata:
    """Returns the metadata associated with a label."""
    state_machine = _get_state_machine(app, label)

    with app.db.begin() as conn:
        row = conn.execute(
            select([labels.c.metadata, labels.c.deleted]).where(and_(
                labels.c.name == label.name,
                labels.c.state_machine == state_machine.name,
            )),
        ).fetchone()

        if row is None:
            raise UnknownLabel(label)

        metadata, deleted = row
        if deleted:
            raise DeletedLabel(label)

        return metadata


def create_label(app: App, label: LabelRef, metadata: Metadata) -> Metadata:
    """Creates a label and starts it in a state machine."""
    state_machine = _get_state_machine(app, label)

    with app.db.begin() as conn:
        try:
            conn.execute(labels.insert().values(
                name=label.name,
                state_machine=state_machine.name,
                metadata=metadata,
            ))
        except IntegrityError:
            raise LabelAlreadyExists(label)

        _start_state_machine(app, label, conn)
        return metadata
    # TODO progress label outside of transaction


def update_metadata_for_label(
    app: App,
    label: LabelRef,
    update: Metadata,
) -> Metadata:
    """
    Updates the metadata for a label.

    Moves the label through the state machine as appropriate.
    """
    state_machine = _get_state_machine(app, label)

    label_filter = and_(
        labels.c.name == label.name,
        labels.c.state_machine == label.state_machine,
    )

    with app.db.begin() as conn:
        row = conn.execute(
            select([
                labels.c.metadata,
                labels.c.deleted,
            ]).where(label_filter),
        ).fetchone()
        if row is None:
            raise UnknownLabel(label)

        existing_metadata, deleted = row
        if deleted:
            raise DeletedLabel(label)

        new_metadata = dict_merge(existing_metadata, update)

        conn.execute(labels.update().where(label_filter).values(
            metadata=new_metadata,
        ))

        _move_label_for_metadata_change(
            state_machine,
            label,
            update,
            new_metadata,
            conn,
        )

        return new_metadata


def _move_label_for_metadata_change(
    state_machine: StateMachine,
    label: LabelRef,
    update: Metadata,
    metadata: Metadata,
    conn,
) -> None:
    history_entry = conn.execute(
        select([history]).where(and_(
            history.c.label_name == label.name,
            history.c.label_state_machine == label.state_machine,
        )).order_by(
            history.c.created.desc(),
        ).limit(1)
    ).fetchone()

    current_state = state_machine.get_state(history_entry.new_state)
    if isinstance(current_state, Action):
        # Label is in an Action state so there's no trigger to resolve.
        return

    if not any(
        trigger.should_trigger_for_update(update)
        for trigger in current_state.metadata_triggers
    ):
        return

    feeds = feeds_for_state_machine(state_machine)
    exit_condition_context = Context(
        label.name,
        metadata,
        _utcnow(),
        feeds,
        current_state.exit_condition.accessed_variables(),
    )
    can_exit = current_state.exit_condition.run(exit_condition_context)

    if not can_exit:
        return

    destination = choose_next_state(
        state_machine,
        current_state,
        exit_condition_context,
    )

    conn.execute(history.insert().values(
        label_name=label.name,
        label_state_machine=state_machine.name,
        old_state=current_state.name,
        new_state=destination.name,
    ))


def choose_next_state(
    state_machine: StateMachine,
    current_state: State,
    context: Context,
) -> State:
    """Assuming a transition out of a given state, choose a next state."""
    next_state_name = current_state.next_states.next_state_for_label(context)
    return state_machine.get_state(next_state_name)


def delete_label(app: App, label: LabelRef) -> None:
    """
    Deletes the metadata for a label and marks the label as deleted.

    The history for the label is not changed (in order to allow post-hoc
    analysis of the path the label took through the state machine).
    """
    state_machine = _get_state_machine(app, label)

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
