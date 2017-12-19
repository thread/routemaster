"""Public API for state recording subsystem."""

import datetime
import dateutil.tz

from typing import Iterable

from routemaster.app import App
from routemaster.config import StateMachine, State
from routemaster.db import state_machines

from sqlalchemy import select, insert

def record_state_machines(
    app : App,
    machines : Iterable[StateMachine],
) -> None:
    """
    Record the new state as being one set of state machines.

    A ValueError is raised in case of incompatibility between the old and new
    configurations.
    """
    machines = list(machines)

    with app.db.begin() as conn:
        now = datetime.datetime.now(dateutil.tz.tzutc())

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

        print("INSERT", insertions)
        print("DELETE", deletions)
        print("UPDATE", updates)

        if insertions:
            conn.execute(
                state_machines.insert(),
                [
                    {
                        'name': new_machine,
                        'updated': now,
                    }
                    for new_machine in insertions
                ]
            )

        if deletions:
            conn.execute(
                state_machines.delete().where(
                    state_machines.c.name.in_(list(deletions))
                ),
            )
