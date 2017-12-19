"""The core of the state machine logic."""
import datetime
from typing import Any, Dict, Iterable, NamedTuple

import dateutil.tz
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.utils import dict_merge
from routemaster.config import State, Action, StateMachine
from routemaster.exit_conditions import Context
from routemaster.state_machine.exceptions import (
    UnknownLabel,
    LabelAlreadyExists,
    UnknownStateMachine,
)


class Label(NamedTuple):
    """API representation of a label for the state machine."""
    name: str
    state_machine: str


Metadata = Dict[str, Any]


def list_labels(app: App, state_machine: StateMachine) -> Iterable[Label]:
    """
    Returns a sorted iterable of labels associated with a state machine.

    Labels are returned ordered alphabetically by name.
    """
    with app.db.begin() as conn:
        label_names = conn.execute(
            select([
                labels.c.name,
            ]).where(
                labels.c.state_machine == state_machine.name,
            ).order_by(
                labels.c.name,
            ),
        )
        for row in label_names:
            yield Label(row[labels.c.name], state_machine.name)


def get_label_metadata(app: App, label: Label) -> Metadata:
    """Returns the metadata associated with a label."""
    with app.db.begin() as conn:
        metadata = conn.scalar(
            select([labels.c.metadata]).where(and_(
                labels.c.name == label.name,
                labels.c.state_machine == label.state_machine,
            )),
        )
        if metadata is None:
            raise UnknownLabel(label)
        return metadata


def create_label(app: App, label: Label, metadata: Metadata) -> Metadata:
    """Creates a label and starts it in a state machine."""
    try:
        state_machine = app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)

    with app.db.begin() as conn:
        try:
            conn.execute(labels.insert().values(
                name=label.name,
                state_machine=state_machine.name,
                metadata=metadata,
            ))
        except IntegrityError:
            raise LabelAlreadyExists(label)

        _start_state_machine(state_machine, label, conn)
        return metadata


def _start_state_machine(
    state_machine: StateMachine,
    label: Label,
    conn,
) -> None:
    conn.execute(history.insert().values(
        label_name=label.name,
        label_state_machine=label.state_machine,
        old_state=None,
        new_state=state_machine.states[0].name,
    ))


def update_metadata_for_label(
    app: App,
    label: Label,
    update: Metadata,
) -> Metadata:
    """
    Updates the metadata for a label.

    Moves the label through the state machine as appropriate.
    """
    try:
        state_machine = app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)

    metadata_field = labels.c.metadata
    label_filter = and_(
        labels.c.name == label.name,
        labels.c.state_machine == label.state_machine,
    )

    with app.db.begin() as conn:
        existing_metadata = conn.scalar(
            select([metadata_field]).where(label_filter),
        )
        if existing_metadata is None:
            raise UnknownLabel(label)

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
    label: Label,
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
        t.should_trigger_for_update(update)
        for t in current_state.metadata_triggers
    ):
        return

    now = datetime.datetime.now(dateutil.tz.tzutc())

    context = Context({'metadata': metadata})
    can_exit = current_state.exit_condition.run(context, now)

    if not can_exit:
        return

    destination = _choose_destination(
        state_machine,
        label,
        current_state,
        metadata,
    )

    conn.execute(history.insert().values(
        label_name=label.name,
        label_state_machine=state_machine.name,
        old_state=current_state.name,
        new_state=destination.name,
    ))


def _choose_destination(
    state_machine: StateMachine,
    label: Label,
    current_state: State,
    metadata: Metadata,
) -> State:
    next_state_name = current_state.next_states.next_state_for_label(metadata)
    return state_machine.get_state(next_state_name)
