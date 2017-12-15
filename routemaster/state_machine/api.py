"""The core of the state machine logic."""
import datetime
from typing import Any, Dict, NamedTuple

from sqlalchemy import and_
from sqlalchemy.sql import select, func

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.utils import dict_merge
from routemaster.config import State, Action, StateMachine
from routemaster.state_machine.exceptions import (
    UnknownLabel,
    UnknownStateMachine,
)


class Label(NamedTuple):
    """API representation of a label for the state machine."""
    name: str
    state_machine: str


Context = Dict[str, Any]


def get_label_context(app: App, label: Label):
    """Returns the context associated with a label."""
    with app.db.begin() as conn:
        context = conn.scalar(
            select([labels.c.context]).where(and_(
                labels.c.name == label.name,
                labels.c.state_machine == label.state_machine,
            )),
        )
        if context is None:
            raise UnknownLabel(label)
        return context


def create_label(app: App, label: Label, context: Context):
    """Creates a label and starts it in a state machine."""
    try:
        state_machine = app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)

    with app.db.begin() as conn:
        conn.execute(labels.insert().values(
            name=label.name,
            state_machine=state_machine.name,
            context=context,
        ))
        _start_state_machine(state_machine, label, conn)
        return context


def _start_state_machine(state_machine: StateMachine, label: Label, conn):
    conn.execute(history.insert().values(
        label_name=label.name,
        label_state_machine=label.state_machine,
        old_state=None,
        new_state=state_machine.states[0].name,
    ))


def update_context_for_label(app: App, label: Label, update: Context):
    """
    Updates the context for a label.

    Moves the label through the state machine as appropriate.
    """
    try:
        state_machine = app.config.state_machines[label.state_machine]
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
            raise UnknownLabel(label)

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
):
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
        for t in current_state.context_triggers
    ):
        return

    elapsed = (datetime.datetime.utcnow() - history.created).total_seconds

    exit_condition_variables = {'context': context}
    can_exit = current_state.exit_condition.run(
        exit_condition_variables,
        elapsed,
    )

    if not can_exit:
        return

    destination = _choose_destination(
        state_machine,
        label,
        current_state,
        context,
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
    context: Context,
) -> State:
    next_state_name = current_state.next_states.next_state_for_label(context)
    return state_machine.get_state(next_state_name)
