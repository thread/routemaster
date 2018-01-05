"""Utilities for state machine execution."""

import datetime
from typing import Any, Dict, Tuple

import dateutil.tz
from sqlalchemy import and_
from sqlalchemy.sql import select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.config import Gate, State, StateMachine
from routemaster.context import Context
from routemaster.state_machine.types import LabelRef, Metadata
from routemaster.state_machine.exceptions import (
    UnknownLabel,
    UnknownStateMachine,
)


def _get_state_machine(app: App, label: LabelRef) -> StateMachine:
    try:
        return app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)


def _utcnow():
    return datetime.datetime.now(dateutil.tz.tzutc())


def _start_state_machine(app: App, label: LabelRef, conn) -> None:
    state_machine = _get_state_machine(app, label)
    conn.execute(history.insert().values(
        label_name=label.name,
        label_state_machine=label.state_machine,
        old_state=None,
        new_state=state_machine.states[0].name,
    ))


def _choose_next_state(
    state_machine: StateMachine,
    current_state: State,
    context: Context,
) -> State:
    """Assuming a transition out of a given state, choose a next state."""
    next_state_name = current_state.next_states.next_state_for_label(context)
    return state_machine.get_state(next_state_name)


def _get_label_metadata(
    label: LabelRef,
    state_machine: StateMachine,
    conn,
) -> Tuple[Dict[str, Any], bool]:
    return conn.execute(
        select([labels.c.metadata, labels.c.deleted]).where(and_(
            labels.c.name == label.name,
            labels.c.state_machine == state_machine.name,
        )),
    ).fetchone()


def _get_current_state(
    label: LabelRef,
    state_machine: StateMachine,
    conn,
) -> State:
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

    return state_machine.get_state(history_entry.new_state)


def _needs_gate_evaluation_for_metadata_change(
    state_machine: StateMachine,
    label: LabelRef,
    update: Metadata,
    conn,
) -> bool:
    current_state = _get_current_state(label, state_machine, conn)
    if not isinstance(current_state, Gate):
        # Label is not a gate state so there's no trigger to resolve.
        return False

    if any(
        trigger.should_trigger_for_update(update)
        for trigger in current_state.metadata_triggers
    ):
        return True

    return False


def _lock_label(label: LabelRef, conn):
    row = conn.execute(
        labels.select().where(
            and_(
                labels.c.name == label.name,
                labels.c.state_machine == label.state_machine,
            ),
        ).with_for_update()
    ).fetchone()

    if not row:
        raise UnknownLabel(label)
