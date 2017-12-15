"""The core of the state machine logic."""
from typing import Any, Dict, NamedTuple

from sqlalchemy import and_
from sqlalchemy.sql import select

from routemaster.db import labels
from routemaster.app import App
from routemaster.utils import dict_merge
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
    with app.db.begin() as conn:
        result = conn.execute(
            select([labels.c.context]).where(and_(
                labels.c.name == label.name,
                labels.c.state_machine == label.state_machine,
            )),
        )
        context = result.fetchone()
        if not context:
            raise UnknownLabel(label)
        return context[labels.c.context]


def create_label(app: App, label: Label, context: Context):
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
        return context


def _start_state_machine(label: Label):
    pass


def update_context_for_label(app: App, label: Label, context: Context):
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

        new_context = dict_merge(existing_context, context)

        conn.execute(labels.update().where(label_filter).values(
            context=new_context,
        ))

        return new_context
