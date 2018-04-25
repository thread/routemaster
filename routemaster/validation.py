"""Validation of state machines."""
import collections

import networkx
from sqlalchemy import func

from routemaster.db import History
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
    with app.new_session():
        _validate_route_start_to_end(state_machine)
        _validate_all_states_exist(state_machine)
        _validate_no_labels_in_nonexistent_states(state_machine, app)
        _validate_unique_state_names(state_machine)


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


def _validate_unique_state_names(state_machine):
    state_name_counts = collections.Counter([
        x.name for x in state_machine.states
    ])

    invalid_states = [x for x, y in state_name_counts.items() if y > 1]

    if invalid_states:
        raise ValidationError(
            f"States {invalid_states!r} are not unique in "
            f"{state_machine.name}",
        )


def _validate_all_states_exist(state_machine):
    state_names = set(x.name for x in state_machine.states)
    for state in state_machine.states:
        for destination_name in state.next_states.all_destinations():
            if destination_name not in state_names:
                raise ValidationError(f"{destination_name} does not exist")


def _validate_no_labels_in_nonexistent_states(state_machine, app):
    states = [x.name for x in state_machine.states]

    states_by_rank = app.session.query(
        History.label_name,
        History.new_state,
        func.row_number().over(
            order_by=History.id.desc(),
            partition_by=History.label_name,
        ).label('rank'),
    ).filter_by(
        label_state_machine=state_machine.name,
    ).subquery()

    invalid_labels_and_states = app.session.query(
        states_by_rank.c.label_name,
        states_by_rank.c.new_state,
    ).filter(
        states_by_rank.c.rank == 1,
        ~(
            states_by_rank.c.new_state.in_(states) |
            states_by_rank.c.new_state.is_(None)
        ),
    ).all()

    if invalid_labels_and_states:
        raise ValidationError(
            f"{len(invalid_labels_and_states)} nodes in states that no "
            f"longer exist",
        )
