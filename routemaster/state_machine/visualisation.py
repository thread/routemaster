"""Visualisation code for state machines."""

from routemaster.config import Action, StateMachine

from typing import List, Dict, Union


def convert_to_network(
    state_machine: StateMachine,
) -> List[Dict[str, Union[Dict[str, str], str]]]:
    """Produce an SVG drawing of a state machine."""
    elements = []

    for state in state_machine.states:
        node_kind = 'action' if isinstance(state, Action) else 'gate'
        elements.append({
            'data': {
                'id': state.name,
                'name': state.name,
            },
            'classes': node_kind,
        })

        all_destinations = state.next_states.all_destinations()
        for destination_name in all_destinations:
            elements.append({'data': {
                'source': state.name,
                'target': destination_name,
            }})

    return elements
