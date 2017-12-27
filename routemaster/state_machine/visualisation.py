"""Visualisation code for state machines."""

import pydot

from routemaster.config import StateMachine


def draw_state_machine(state_machine: StateMachine) -> bytes:
    """Produce an SVG drawing of a state machine."""
    graph = pydot.Dot(graph_type='graph')

    for state in state_machine.states:
        graph.add_node(pydot.Node(state.name))
        for destination_name in state.next_states.all_destinations():
            graph.add_edge(pydot.Edge(state.name, destination_name))

    return graph.create(format='svg')
