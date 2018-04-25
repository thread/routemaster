"""Visualisation code for state machines."""

from routemaster.config import Action, StateMachine


def convert_to_network(state_machine: StateMachine) -> bytes:
    """Produce an SVG drawing of a state machine."""
    graph = {
        'nodes': [],
        'edges': [],
    }

    for state in state_machine.states:
        node_kind = 'action' if isinstance(state, Action) else 'gate'
        graph['nodes'].append({
            'data': {
                'id': state.name,
                'name': state.name,
            },
            'classes': node_kind,
        })

        all_destinations = state.next_states.all_destinations()
        for destination_name in all_destinations:
            graph['edges'].append({'data': {
                'source': state.name,
                'target': destination_name,
            }})

    return graph
