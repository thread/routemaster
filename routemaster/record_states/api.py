"""Public API for state recording subsystem."""

from typing import Iterable

from sqlalchemy import func, select

from routemaster.db import state_machines
from routemaster.app import App
from routemaster.config import StateMachine
from routemaster.record_states.utils import (
    resync_state_machine_names,
    resync_states_on_state_machine,
)


def record_state_machines(
    app: App,
    machines: Iterable[StateMachine],
) -> None:
    """
    Record the new state as being one set of state machines.

    A ValueError is raised in case of incompatibility between the old and new
    configurations.
    """
    machines = list(machines)
    machines_by_name = {x.name: x for x in machines}

    with app.db.begin() as conn:
        old_machine_names = set(
            x.name
            for x in conn.execute(
                select((
                    state_machines.c.name,
                )),
            ).fetchall()
        )

        resync_machines = resync_state_machine_names(
            conn,
            old_machine_names,
            machines,
        )

        updated_state_machine_names = set()

        for machine_name in resync_machines:
            machine = machines_by_name[machine_name]

            any_changes = resync_states_on_state_machine(conn, machine)
            if any_changes:
                updated_state_machine_names.add(machine.name)

        updated_state_machine_names &= old_machine_names

        if updated_state_machine_names:
            conn.execute(
                state_machines.update().where(
                    state_machines.c.name.in_(updated_state_machine_names),
                ).values(
                    updated=func.now(),
                )
            )
