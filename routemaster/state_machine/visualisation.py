"""Visualisation code for state machines."""

from typing import Dict, List, Union

from routemaster.config import Action, StateMachine

CytoscapeData = List[Dict[str, Union[Dict[str, str], str]]]


def nodes_for_cytoscape(
    state_machine: StateMachine,
) -> CytoscapeData:
    """Produce an SVG drawing of a state machine."""
    elements: CytoscapeData = []

    for state in state_machine.states:
        node_kind = 'action' if isinstance(state, Action) else 'gate'
        elements.append({
            'data': {'id': state.name},
            'classes': node_kind,
        })

        destinations = state.next_states.destinations_for_render()
        for destination_name, reason in destinations.items():
            elements.append({'data': {
                'source': state.name,
                'target': destination_name,
                'label': reason,
            }})

    return elements
