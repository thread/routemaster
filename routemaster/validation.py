"""Validation of state machines."""
import networkx
from sqlalchemy import and_, func

from routemaster.db import labels, history
from routemaster.app import App
from routemaster.config import StateMachine


async def validate(app: App, state_machine: StateMachine):
    """Validate that a given state machine is internally consistent."""
    _validate_route_start_to_end(state_machine)
    _validate_all_states_exist(state_machine)
    await _validate_no_labels_in_nonexistent_states(state_machine, app)


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
        raise ValueError("Graph is not fully connected")


def _validate_all_states_exist(state_machine):
    state_names = set(x.name for x in state_machine.states)
    for state in state_machine.states:
        for destination_name in state.next_states.all_destinations():
            if destination_name not in state_names:
                raise ValueError(f"{destination_name} does not exist")


async def _validate_no_labels_in_nonexistent_states(state_machine, app):
    states = [x.name for x in state_machine.states]
    async with app.db.begin() as conn:
        current_states = history.select(
            history.c.label_name,
            history.c.state_machine_name,
            history.c.new_state,
            func.max(history.c.created),
        ).group_by(
            history.label_name,
            history.label_state_machine,
        )

        labels_in_invalid_states = current_states.select(
            history.new_state,
        ).join(
            labels,
            and_(
                labels.c.name == history.c.label_name,
                labels.c.state_machine == history.c.label_state_machine,
                ~history.c.new_state.in_(states),
            ),
        )

        result = await conn.scalar(labels_in_invalid_states)
        count = await result.fetchone()
        if count != 0:
            raise ValueError(f"{count} nodes in states that no longer exist")
