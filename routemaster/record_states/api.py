"""Public API for state recording subsystem."""

from typing import Iterable

from sqlalchemy import select, func

from record_states.utils import _resync_states_on_state_machine
from routemaster.db import states, state_machines
from routemaster.app import App
from routemaster.config import StateMachine


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
    machines_by_name = {
        x.name: x
        for x in machines
    }

    with app.db.begin() as conn:
        old_machine_names = set(
            x.name
            for x in conn.execute(
                select((
                    state_machines.c.name,
                )),
            ).fetchall()
        )

        new_machine_names = set(
            x.name
            for x in machines
        )

        insertions = new_machine_names - old_machine_names
        deletions = old_machine_names - new_machine_names
        updates = new_machine_names & old_machine_names

        if insertions:
            conn.execute(
                state_machines.insert().values(updated=func.now()),
                [
                    {
                        'name': new_machine,
                    }
                    for new_machine in insertions
                ]
            )

        if deletions:
            conn.execute(
                states.delete().where(
                    states.c.state_machine.in_(list(deletions)),
                ),
            )
            conn.execute(
                state_machines.delete().where(
                    state_machines.c.name.in_(list(deletions)),
                ),
            )

        resync_machines = updates | insertions
        updated_state_machine_names = set()

        for machine_name in resync_machines:
            machine = machines_by_name[machine_name]

            any_changes = _resync_states_on_state_machine(conn, machine)
            if any_changes:
                updated_state_machine_names.add(machine.name)

        updated_state_machine_names -= insertions

        if updated_state_machine_names:
            conn.execute(
                state_machines.update().where(
                    state_machines.c.name.in_(updated_state_machine_names),
                ).values(
                    updated=func.now(),
                )
            )


