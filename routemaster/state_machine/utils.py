"""Utilities for state machine execution."""

import datetime
from typing import Any, Dict, List, Tuple

import dateutil.tz
from sqlalchemy import and_, func, select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.feeds import feeds_for_state_machine
from routemaster.config import (
    Gate,
    State,
    Action,
    StateMachine,
    ContextNextStates,
)
from routemaster.context import Context
from routemaster.state_machine.types import LabelRef, Metadata
from routemaster.state_machine.exceptions import (
    DeletedLabel,
    UnknownLabel,
    UnknownStateMachine,
)


def get_state_machine(app: App, label: LabelRef) -> StateMachine:
    """Finds the state machine instance by name in the app config."""
    try:
        return app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)


def start_state_machine(app: App, label: LabelRef, conn) -> None:
    """Create the first history entry for a label in a state machine."""
    state_machine = get_state_machine(app, label)
    conn.execute(history.insert().values(
        label_name=label.name,
        label_state_machine=label.state_machine,
        old_state=None,
        new_state=state_machine.states[0].name,
    ))


def choose_next_state(
    state_machine: StateMachine,
    current_state: State,
    context: Context,
) -> State:
    """Assuming a transition is valid, choose a next state."""
    next_state_name = current_state.next_states.next_state_for_label(context)
    return state_machine.get_state(next_state_name)


def get_label_metadata(
    label: LabelRef,
    state_machine: StateMachine,
    conn,
) -> Tuple[Dict[str, Any], bool]:
    """Get the metadata and whether the label has been deleted."""
    return conn.execute(
        select([labels.c.metadata, labels.c.deleted]).where(and_(
            labels.c.name == label.name,
            labels.c.state_machine == state_machine.name,
        )),
    ).fetchone()


def get_current_state(
    label: LabelRef,
    state_machine: StateMachine,
    conn,
) -> State:
    """Get the current state of a label, based on its last history entry."""
    history_entry = conn.execute(
        select([history]).where(and_(
            history.c.label_name == label.name,
            history.c.label_state_machine == state_machine.name,
        )).order_by(
            history.c.created.desc(),
        ).limit(1),
    ).fetchone()

    if history_entry is None:
        raise UnknownLabel(label)

    return state_machine.get_state(history_entry.new_state)


def get_current_history_id(
    label: LabelRef,
    state_machine: StateMachine,
    conn,
) -> int:
    """Get the id of a label's last history entry."""
    history_id = conn.execute(
        select([history.c.id]).where(and_(
            history.c.label_name == label.name,
            history.c.label_state_machine == state_machine.name,
        )).order_by(
            history.c.created.desc(),
        ).limit(1),
    ).scalar()

    if history_id is None:
        raise UnknownLabel(label)

    return history_id


def needs_gate_evaluation_for_metadata_change(
    state_machine: StateMachine,
    label: LabelRef,
    update: Metadata,
    conn,
) -> Tuple[bool, State]:
    """
    Given a change to the metadata, should the gate evaluation be triggered.
    """

    current_state = get_current_state(label, state_machine, conn)

    if not isinstance(current_state, Gate):
        # Label is not a gate state so there's no trigger to resolve.
        return False, current_state

    if any(
        trigger.should_trigger_for_update(update)
        for trigger in current_state.metadata_triggers
    ):
        return True, current_state

    return False, current_state


def lock_label(label: LabelRef, conn):
    """Lock a label in the current transaction."""
    row = conn.execute(
        labels.select().where(
            and_(
                labels.c.name == label.name,
                labels.c.state_machine == label.state_machine,
            ),
        ).with_for_update(),
    ).fetchone()

    if row is None:
        raise UnknownLabel(label)

    return row


def labels_to_retry_for_action(
    state_machine: StateMachine,
    action: Action,
    conn,
) -> Dict[str, Metadata]:
    """Util to get all the labels in an action state that need retrying."""
    ranked_transitions = select((
        history.c.label_name,
        history.c.old_state,
        history.c.new_state,
        func.row_number().over(
            order_by=history.c.created.desc(),
            partition_by=history.c.label_name,
        ).label('rank'),
    )).where(
        history.c.label_state_machine == state_machine.name,
    ).alias('transitions')

    active_participants = select((
        ranked_transitions.c.label_name,
        labels.c.metadata,
    )).where(and_(
        ranked_transitions.c.new_state == action.name,
        ranked_transitions.c.rank == 1,
        ranked_transitions.c.label_name == labels.c.name,
        labels.c.state_machine == state_machine.name,
    ))

    return {
        x.label_name: x.metadata
        for x in conn.execute(active_participants)
    }


def context_for_label(
    label: LabelRef,
    metadata: Metadata,
    state_machine: StateMachine,
    state: State,
) -> Context:
    """Util to build the context for a label in a state."""
    feeds = feeds_for_state_machine(state_machine)

    accessed_variables: List[str] = []
    if isinstance(state, Gate):
        accessed_variables.extend(state.exit_condition.accessed_variables())
    if isinstance(state.next_states, ContextNextStates):
        accessed_variables.append(state.next_states.path)

    return Context(
        label.name,
        metadata,
        datetime.datetime.now(dateutil.tz.tzutc()),
        feeds,
        accessed_variables,
    )


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
                from routemaster.state_machine.actions import process_action
                return process_action(
                    app,
                    current_state,
                    label,
                    conn,
                )

            elif isinstance(current_state, Gate):  # pragma: no branch
                if not current_state.trigger_on_entry:
                    return False
                from routemaster.state_machine.gates import process_gate

                return process_gate(
                    app,
                    current_state,
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
            # not even a warning, and we should allow the retry process to
            # continue.
            pass
