"""Validation of state machines."""
import networkx
from sqlalchemy import and_, func, false, select

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.config import Config, StateMachine


class ValidationError(Exception):
    """Class for errors raised to indicate invalid configuration."""
    pass


def validate_config(app: App, config: Config):
    """Validate that a given config satisfies invariants."""
    for state_machine in config.state_machines.values():
        _validate_state_machine(app, state_machine)


def _validate_state_machine(app: App, state_machine: StateMachine):
    """Validate that a given state machine is internally consistent."""
    _validate_route_start_to_end(state_machine)
    _validate_all_states_exist(state_machine)
    _validate_no_labels_in_nonexistent_states(state_machine, app)


def _build_graph(state_machine: StateMachine) -> networkx.Graph:
    graph = networkx.Graph()
    for state in state_machine.states:
        graph.add_node(state.name)
        for destination_name in state.next_states.all_destinations():
            graph.add_edge(state.name, destination_name)
    return graph


def _validate_route_start_to_end(state_machine):
    graph = _build_graph(state_machine)
    if not networkx.is_connected(graph):
        raise ValidationError("Graph is not fully connected")


def _validate_all_states_exist(state_machine):
    state_names = set(x.name for x in state_machine.states)
    for state in state_machine.states:
        for destination_name in state.next_states.all_destinations():
            if destination_name not in state_names:
                raise ValidationError(f"{destination_name} does not exist")


def _validate_no_labels_in_nonexistent_states(state_machine, app):
    states = [x.name for x in state_machine.states]

    with app.db.begin() as conn:

        latest_states = select([
            func.max(history.c.created).label('latest'),
            history.c.label_name,
            history.c.label_state_machine,
        ]).group_by(
            history.c.label_name,
            history.c.label_state_machine,
        ).alias('latest_states')

        invalid_states = select([
            history.c.new_state,
            func.count(history.c.id),
        ]).select_from(
            history.join(
                latest_states,
                and_(
                    latest_states.c.label_name == history.c.label_name,
                    latest_states.c.latest == history.c.created,
                    (
                        latest_states.c.label_state_machine ==
                        history.c.label_state_machine
                    ),
                ),
            ).join(
                labels,
                and_(
                    labels.c.name == history.c.label_name,
                    labels.c.state_machine == history.c.label_state_machine,
                ),
            ),
        ).where(
            and_(
                labels.c.deleted == false(),
                ~history.c.new_state.in_(states),
            ),
        ).group_by(
            history.c.label_name,
            history.c.label_state_machine,
            history.c.new_state,
        )

        result = conn.execute(invalid_states)
        inhabited = dict(result.fetchall())
        if inhabited:
            raise ValidationError(
                f"Labels currently in states that no longer exist: "
                f"{', '.join(inhabited)}",
            )
