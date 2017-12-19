"""Public API for state recording subsystem."""

import datetime
from typing import Iterable

import dateutil.tz
from sqlalchemy import and_, not_, select

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

            old_states = set(
                x.name
                for x in conn.execute(
                    select((
                        states.c.name,
                    )).where(
                        and_(
                            states.c.state_machine == machine.name,
                            not_(states.c.deprecated),
                        ),
                    )
                )
            )

            new_states = set(
                x.name
                for x in machine.states
            )

            deleted_states = old_states - new_states
            created_states = new_states - old_states

            if deleted_states:
                conn.execute(
                    states.update().where(
                        and_(
                            states.c.state_machine == machine.name,
                            states.c.name.in_(list(deleted_states)),
                        ),
                    ).values(
                        deprecated=True,
                    )
                )

            if created_states:
                # TODO: Handle the case where dead states are brought back to
                # life.
                conn.execute(
                    states.insert(),
                    [
                        {
                            'state_machine': machine.name,
                            'name': state.name,
                            'updated': now,
                        }
                        for state in machine.states
                        if state.name in created_states
                    ]
                )

            if deleted_states or created_states:
                updated_state_machine_names.add(machine.name)

        updated_state_machine_names -= insertions

        if updated_state_machine_names:
            conn.execute(
                state_machines.update().where(
                    state_machines.c.name.in_(updated_state_machine_names),
                ).values(
                    updated=now,
                )
            )
