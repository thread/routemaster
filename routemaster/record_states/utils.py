"""Utility methods for state resyncing."""

from typing import Set, Iterable, Tuple

from sqlalchemy import and_, or_, func, not_, select, tuple_

from routemaster.db import states, state_machines, edges
from routemaster.config import StateMachine


def resync_state_machine_names(
    conn,
    old_machine_names: Set[str],
    machines: Iterable[StateMachine],
) -> Set[str]:
    """
    Resync the state machines by name.

    Return a collection of the name of the machines which were either updated
    or created.
    """

    new_machine_names = set(x.name for x in machines)

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

    return updates | insertions


def resync_states_on_state_machine(conn, machine: StateMachine) -> bool:
    """
    Resync all states for the given state machine.

    Return whether any work was done.
    """

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
        deprecate_states(conn, machine, deleted_states)

    if created_states:
        create_or_undeprecate_states(conn, machine, created_states)

    all_links = set(
        (x.name, y)
        for x in machine.states
        for y in x.next_states.all_destinations()
    )

    changed_links = resync_links(
        conn,
        machine,
        all_links,
    )

    any_changes = bool(changed_links or deleted_states or created_states)
    return any_changes


def resync_links(
    conn,
    machine: StateMachine,
    links: Set[Tuple[str, str]],
) -> bool:
    """Synchronise the links table for this machine."""
    anything_done = False

    # Deprecate all links not in this set, which are not already deprecated
    result = conn.execute(
        edges.update().where(
            and_(
                edges.c.state_machine == machine.name,
                not_(
                    tuple_(
                        edges.c.from_state,
                        edges.c.to_state,
                    ).in_(list(links)),
                ),
                not_(edges.c.deprecated),
            ),
        ).values(
            deprecated=True,
            updated=func.now(),
        ),
    )
    if result.rowcount > 0:
        anything_done = True

    previous_data = {
        (x.from_state, x.to_state): x.deprecated
        for x in conn.execute(
            select((
                edges.c.from_state,
                edges.c.to_state,
                edges.c.deprecated,
            )).where(
                edges.c.state_machine == machine.name,
            )
        )
    }
    new_inserts = links - set(previous_data)
    undeprecations = links & set(
        link
        for link, deprecated in previous_data.items()
        if deprecated
    )

    if new_inserts:
        conn.execute(
            edges.insert().values(
                state_machine=machine.name,
                deprecated=False,
                updated=func.now(),
            ),
            [
                {
                    'from_state': from_state,
                    'to_state': to_state,
                }
                for from_state, to_state in new_inserts
            ],
        )
        anything_done = True

    if undeprecations:
        conn.execute(
            edges.update().values(
                deprecated=False,
                updated=func.now(),
            ).where(
                tuple_(
                    edges.c.from_state,
                    edges.c.to_state,
                ).in_(list(undeprecations)),
            ),
        )
        anything_done = True

    return anything_done


def create_or_undeprecate_states(
    conn,
    machine: StateMachine,
    created_states: Set[str],
) -> None:
    """Create some new states, or mark them as undeprecated."""
    # If any of these are old states which have been reanimated, we
    # just set the deprecated flag back to False and flag them
    # updated.
    undeprecated_names = [
        x.name
        for x in conn.execute(
            states.update().where(
                and_(
                    states.c.state_machine == machine.name,
                    states.c.name.in_(list(created_states)),
                    states.c.deprecated,
                ),
            ).values(
                deprecated=False,
                updated=func.now(),
            ).returning(
                states.c.name,
            ),
        )
    ]

    newly_inserted_rows = [
        {
            'name': state.name,
        }
        for state in machine.states
        if state.name in created_states and
        state.name not in undeprecated_names
    ]

    if newly_inserted_rows:
        conn.execute(states.insert().values(
            state_machine=machine.name,
            updated=func.now(),
        ), newly_inserted_rows)


def deprecate_states(
    conn,
    machine: StateMachine,
    deleted_states: Set[str],
) -> None:
    """Mark states as deprecated."""
    conn.execute(
        states.update().where(
            and_(
                states.c.state_machine == machine.name,
                states.c.name.in_(list(deleted_states)),
            ),
        ).values(
            deprecated=True,
            updated=func.now(),
        )
    )
