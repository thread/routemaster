"""Visualisation code for state machines."""

import pydot

from routemaster.config import Action, StateMachine


def draw_state_machine(state_machine: StateMachine) -> bytes:
    """Produce an SVG drawing of a state machine."""
    graph = pydot.Dot(
        graph_type='graph',
        label=state_machine.name,
        labelloc='t',
        labeljust='l',
    )

    for state in state_machine.states:
        node_colour = 'red' if isinstance(state, Action) else 'blue'
        graph.add_node(pydot.Node(state.name, color=node_colour, shape='rect'))

        all_destinations = state.next_states.all_destinations()
        for destination_name in all_destinations:
            edge = pydot.Edge(
                state.name,
                destination_name,
                dir='forward',
                style='dashed' if len(all_destinations) > 1 else 'solid',
            )
            graph.add_edge(edge)

    return graph.create(format='svg')
