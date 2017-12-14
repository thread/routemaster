"""Validation of state machines."""
import networkx

from routemaster.app import App
from routemaster.config import StateMachine


def validate(app: App, state_machine: StateMachine):
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
        raise ValueError("Graph is not fully connected")


def _validate_all_states_exist(state_machine):
    state_names = set(x.name for x in state_machine.states)
    for state in state_machine.states:
        for destination_name in state.next_states.all_destinations():
            if destination_name not in state_names:
                raise ValueError(f"{destination_name} does not exist")


def _validate_no_labels_in_nonexistent_states(state_machine, app):
    pass
