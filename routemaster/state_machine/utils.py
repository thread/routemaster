"""Utilities for state machine execution."""

import datetime

import dateutil.tz

from routemaster.db import history
from routemaster.app import App
from routemaster.config import StateMachine
from routemaster.state_machine.types import LabelRef
from routemaster.state_machine.exceptions import UnknownStateMachine


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
