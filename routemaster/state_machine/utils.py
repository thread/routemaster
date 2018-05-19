"""Utilities for state machine execution."""

import datetime
import functools
import contextlib
from typing import Any, Dict, List, Tuple, Optional

import dateutil.tz
from sqlalchemy import func

from routemaster.db import Label, History
from routemaster.app import App
from routemaster.feeds import feeds_for_state_machine
from routemaster.config import Gate, State, StateMachine, ContextNextStates
from routemaster.context import Context
from routemaster.logging import BaseLogger
from routemaster.state_machine.types import LabelRef, Metadata
from routemaster.state_machine.exceptions import (
    UnknownLabel,
    UnknownStateMachine,
)


def get_state_machine(app: App, label: LabelRef) -> StateMachine:
    """Finds the state machine instance by name in the app config."""
    try:
        return app.config.state_machines[label.state_machine]
    except KeyError as k:
        raise UnknownStateMachine(label.state_machine)


def choose_next_state(
    state_machine: StateMachine,
    current_state: State,
    context: Context,
) -> State:
    """Assuming a transition is valid, choose a next state."""
    next_state_name = current_state.next_states.next_state_for_label(context)
    return state_machine.get_state(next_state_name)


def get_label_metadata(
    app: App,
    label: LabelRef,
    state_machine: StateMachine,
) -> Tuple[Dict[str, Any], bool]:
    """Get the metadata and whether the label has been deleted."""
    return app.session.query(Label.metadata, Label.deleted).filter_by(
        name=label.name,
        state_machine=state_machine.name,
    ).first()


def get_current_state(
    app: App,
    label: LabelRef,
    state_machine: StateMachine,
) -> Optional[State]:
    """Get the current state of a label, based on its last history entry."""
    history_entry = get_current_history(app, label)
    if history_entry.new_state is None:
        # label has been deleted
        return None
    return state_machine.get_state(history_entry.new_state)


def get_current_history(app: App, label: LabelRef) -> History:
    """Get a label's last history entry."""
    history_entry = app.session.query(History).filter_by(
        label_name=label.name,
        label_state_machine=label.state_machine,
    ).order_by(
        # Our model type stubs define the `id` attribute as `int`, yet
        # sqlalchemy actually allows the attribute to be used for ordering like
        # this; ignore the type check here specifically rather than complicate
        # our type definitions.
        History.id.desc(),  # type: ignore
    ).first()

    if history_entry is None:
        raise UnknownLabel(label)

    return history_entry


def needs_gate_evaluation_for_metadata_change(
    app: App,
    state_machine: StateMachine,
    label: LabelRef,
    update: Metadata,
) -> Tuple[bool, State]:
    """
    Given a change to the metadata, should the gate evaluation be triggered.
    """

    current_state = get_current_state(app, label, state_machine)

    if current_state is None:
        raise ValueError(
            f"Cannot determine gate evaluation for deleted label {label} "
            "(deleted labels have no current state)",
        )

    if not isinstance(current_state, Gate):
        # Label is not a gate state so there's no trigger to resolve.
        return False, current_state

    if any(
        trigger.should_trigger_for_update(update)
        for trigger in current_state.metadata_triggers
    ):
        return True, current_state

    return False, current_state


def lock_label(app: App, label: LabelRef) -> Label:
    """Lock a label in the current transaction."""
    row = app.session.query(Label).filter_by(
        name=label.name,
        state_machine=label.state_machine,
    ).with_for_update().first()

    if row is None:
        raise UnknownLabel(label)

    return row


def labels_in_state(
    app: App,
    state_machine: StateMachine,
    state: State,
) -> List[str]:
    """Util to get all the labels in an action state that need retrying."""
    return _labels_in_state(app, state_machine, state, True)


def labels_needing_metadata_update_retry_in_gate(
    app: App,
    state_machine: StateMachine,
    state: State,
) -> List[str]:
    """Util to get all the labels in an action state that need retrying."""
    if not isinstance(state, Gate):  # pragma: no branch
        raise ValueError(  # pragma: no cover
            f"labels_needing_metadata_update_retry_in_gate called with "
            f"{state.name} which is not an Gate",
        )

    return _labels_in_state(
        app,
        state_machine,
        state,
        ~Label.metadata_triggers_processed,
    )


def _labels_in_state(
    app: App,
    state_machine: StateMachine,
    state: State,
    filter_: Any,
) -> List[str]:
    """Util to get all the labels in an action state that need retrying."""

    states_by_rank = app.session.query(
        History.label_name,
        History.new_state,
        func.row_number().over(
            # Our model type stubs define the `id` attribute as `int`, yet
            # sqlalchemy actually allows the attribute to be used for ordering
            # like this; ignore the type check here specifically rather than
            # complicate our type definitions.
            order_by=History.id.desc(),  # type: ignore
            partition_by=History.label_name,
        ).label('rank'),
    ).filter_by(
        label_state_machine=state_machine.name,
    ).subquery()

    ranked_transitions = app.session.query(
        states_by_rank.c.label_name,
    ).filter(
        states_by_rank.c.rank == 1,
        states_by_rank.c.new_state == state.name,
    ).join(Label).filter(
        filter_,
    )

    return [x for x, in ranked_transitions]


def context_for_label(
    label: LabelRef,
    metadata: Metadata,
    state_machine: StateMachine,
    state: State,
    history_entry: Any,
    logger: BaseLogger,
) -> Context:
    """Util to build the context for a label in a state."""
    feeds = feeds_for_state_machine(state_machine)

    accessed_variables: List[str] = []
    if isinstance(state, Gate):
        accessed_variables.extend(state.exit_condition.accessed_variables())
    if isinstance(state.next_states, ContextNextStates):
        accessed_variables.append(state.next_states.path)

    @contextlib.contextmanager
    def feed_logging_context(feed_url):
        with logger.process_feed(state_machine, state, feed_url):
            yield functools.partial(
                logger.feed_response,
                state_machine,
                state,
                feed_url,
            )

    return Context(
        label=label.name,
        metadata=metadata,
        now=datetime.datetime.now(dateutil.tz.tzutc()),
        feeds=feeds,
        accessed_variables=accessed_variables,
        current_history_entry=history_entry,
        feed_logging_context=feed_logging_context,
    )
