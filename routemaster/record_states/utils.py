"""Utility methods for state resyncing."""

from sqlalchemy import and_, func, not_, select

from routemaster.db import states


def resync_states_on_state_machine(conn, machine):
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

    any_changes = deleted_states or created_states
    return any_changes


def create_or_undeprecate_states(conn, machine, created_states):
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


def deprecate_states(conn, machine, deleted_states):
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
