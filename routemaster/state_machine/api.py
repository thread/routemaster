"""The core of the state machine logic."""
import datetime
from typing import Any, Dict, Iterable, NamedTuple

import dateutil.tz

from routemaster.db import Label as DBLabel
from routemaster.db import History as DBHistory
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
    for (name,) in app.session.query(DBLabel.name).filter_by(
        state_machine=state_machine.name,
    ):
        yield Label(name=name, state_machine=state_machine.name)


def get_label_state(app: App, label: Label) -> State:
    """Finds the current state of a label."""
    history_entry = app.session.query(DBHistory).filter_by(
        label_name=label.name,
        label_state_machine=label.state_machine,
    ).order_by(DBHistory.created.desc()).one_or_none()

    if history_entry is None:
        raise UnknownLabel(label)

    current_state = app.config.state_machines[label.state_machine].get_state(
        history_entry.new_state,
    )

    return current_state


def get_label_context(app: App, label: Label) -> Context:
    """Returns the context associated with a label."""
    row = app.session.query(DBLabel).filter_by(
        name=label.name,
        state_machine=label.state_machine,
    ).one_or_none()

    if row is None:
        raise UnknownLabel(label)

    if row.deleted:
        raise DeletedLabel(label)

    return row.context


def create_label(app: App, label: Label, context: Context) -> Context:
    """Creates a label and starts it in a state machine."""
    try:
        state_machine = app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)

    if app.session.query(
        app.session.query(DBLabel).filter_by(
            name=label.name,
            state_machine=label.state_machine,
        ).exists()
    ).scalar():
        raise LabelAlreadyExists(label)

    app.session.add(DBLabel(
        name=label.name,
        state_machine=state_machine.name,
        context=context,
    ))
    app.session.flush()

    _start_state_machine(app, state_machine, label)

    return context


def _start_state_machine(
    app: App,
    state_machine: StateMachine,
    label: Label,
) -> None:
    new_entry = DBHistory(
        label_name=label.name,
        label_state_machine=label.state_machine,
        old_state=None,
        new_state=state_machine.states[0].name,
    )
    app.session.add(new_entry)


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

    instance = app.session.query(DBLabel).filter_by(
        name=label.name,
        state_machine=label.state_machine,
    ).one_or_none()

    if instance is None:
        raise UnknownLabel(label)

    if instance.deleted:
        raise DeletedLabel(label)

    new_context = dict_merge(instance.context, update)
    instance.context = new_context

    _move_label_for_context_change(
        app,
        state_machine,
        label,
        update,
        new_context,
    )

    return new_context


def _move_label_for_context_change(
    app: App,
    state_machine: StateMachine,
    label: Label,
    update: Context,
    context: Context,
) -> None:
    (most_recent_state_name,) = app.session.query(
        DBHistory.new_state,
    ).filter_by(
        label_name=label.name,
        label_state_machine=label.state_machine,
    ).order_by(DBHistory.created.desc()).first()

    current_state = state_machine.get_state(most_recent_state_name)
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

    destination = _choose_destination(state_machine, current_state, context)

    app.session.add(DBHistory(
        label_name=label.name,
        label_state_machine=label.state_machine,
        old_state=current_state.name,
        new_state=destination.name,
    ))


def _choose_destination(
    state_machine: StateMachine,
    current_state: State,
    context: Context,
) -> State:
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

    instance = app.session.query(DBLabel).filter_by(
        name=label.name,
        state_machine=label.state_machine,
    ).one()

    instance.context = {}
    instance.deleted = True

    _exit_state_machine(app, label)


def _exit_state_machine(
    app: App,
    label: Label,
) -> None:
    (most_recent_state,) = app.session.query(DBHistory.new_state).filter_by(
        label_name=label.name,
        label_state_machine=label.state_machine,
    ).order_by(DBHistory.created.desc()).first()

    app.session.add(DBHistory(
        label_name=label.name,
        label_state_machine=label.state_machine,
        old_state=most_recent_state,
        new_state=None,
    ))
