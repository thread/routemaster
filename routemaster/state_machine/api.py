"""The core of the state machine logic."""
import datetime
from typing import Any, Dict, Iterable, NamedTuple

import dateutil.tz
from sqlalchemy import and_, not_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.utils import dict_merge
from routemaster.config import State, Action, StateMachine
from routemaster.state_machine.exceptions import (
    DeletedLabel,
    UnknownLabel,
    LabelAlreadyExists,
    UnknownStateMachine,
)


class Label(NamedTuple):
    """API representation of a label for the state machine."""
    name: str
    state_machine: str


Context = Dict[str, Any]


def _utcnow():
    return datetime.datetime.now(dateutil.tz.tzutc())


def list_labels(app: App, state_machine: StateMachine) -> Iterable[Label]:
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
            yield Label(row[labels.c.name], state_machine.name)


def get_label_state(app: App, label: Label) -> State:
    """Finds the current state of a label."""
    with app.db.begin() as conn:
        history_entry = conn.execute(
            select([history]).where(and_(
                history.c.label_name == label.name,
                history.c.label_state_machine == label.state_machine,
            )).order_by(
                history.c.created.desc(),
            ).limit(1)
        ).fetchone()

    if history_entry is None:
        raise UnknownLabel(label)

    current_state = app.config.state_machines[label.state_machine].get_state(
        history_entry.new_state,
    )

    return current_state


def get_label_context(app: App, label: Label) -> Context:
    """Returns the context associated with a label."""
    with app.db.begin() as conn:
        row = conn.execute(
            select([labels.c.context, labels.c.deleted]).where(and_(
                labels.c.name == label.name,
                labels.c.state_machine == label.state_machine,
            )),
        ).fetchone()

        if row is None:
            raise UnknownLabel(label)

        context, deleted = row
        if deleted:
            raise DeletedLabel(label)

        return context


def create_label(app: App, label: Label, context: Context) -> Context:
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
                context=context,
            ))
        except IntegrityError:
            raise LabelAlreadyExists(label)

        _start_state_machine(state_machine, label, conn)
        return context


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


def update_context_for_label(
    app: App,
    label: Label,
    update: Context,
) -> Context:
    """
    Updates the context for a label.

    Moves the label through the state machine as appropriate.
    """
    try:
        state_machine = app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)

    context_field = labels.c.context
    deleted_field = labels.c.deleted
    label_filter = and_(
        labels.c.name == label.name,
        labels.c.state_machine == label.state_machine,
    )

    with app.db.begin() as conn:
        row = conn.execute(
            select([context_field, deleted_field]).where(label_filter),
        ).fetchone()
        if row is None:
            raise UnknownLabel(label)

        existing_context, deleted = row
        if deleted:
            raise DeletedLabel(label)

        new_context = dict_merge(existing_context, update)

        conn.execute(labels.update().where(label_filter).values(
            context=new_context,
        ))

        _move_label_for_context_change(
            state_machine,
            label,
            update,
            new_context,
            conn,
        )

        return new_context


def _move_label_for_context_change(
    state_machine: StateMachine,
    label: Label,
    update: Context,
    context: Context,
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
        for trigger in current_state.context_triggers
    ):
        return

    exit_condition_variables = {**context}
    can_exit = current_state.exit_condition.run(
        exit_condition_variables,
        _utcnow(),
    )

    if not can_exit:
        return

    destination = choose_next_state(state_machine, current_state, context)

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


def delete_label(app: App, label: Label) -> None:
    """
    Deletes the context for a label and marks the label as deleted.

    The history for the label is not changed (in order to allow post-hoc
    analysis of the path the label took through the state machine).
    """
    try:
        app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)

    context_field = labels.c.context
    label_filter = and_(
        labels.c.name == label.name,
        labels.c.state_machine == label.state_machine,
    )

    with app.db.begin() as conn:
        existing_context = conn.scalar(
            select([context_field]).where(label_filter),
        )
        if existing_context is None:
            return

        conn.execute(labels.update().where(label_filter).values(
            context={},
            deleted=True,
        ))

        _exit_state_machine(label, conn)


def _exit_state_machine(
    label: Label,
    conn,
) -> None:
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
