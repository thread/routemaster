"""Core API endpoints for routemaster service."""

from flask import Flask, abort, jsonify, request

from routemaster import state_machine
from routemaster.state_machine import Label, UnknownLabel, UnknownStateMachine

server = Flask('routemaster')


@server.route('/', methods=['GET'])
def status():
    """Status check endpoint."""
    try:
        with server.config.app.db.begin() as conn:
            conn.execute('select 1')
            return jsonify({'status': 'ok'})
    except Exception:
        return jsonify({'status': 'Could not connect to database'})


@server.route(
    '/state-machines/<state_machine_name>/labels',
    methods=['GET'],
)
def get_labels(state_machine_name):
    """List the labels in a state machine."""
    pass


@server.route(
    '/state-machines/<state_machine_name>/labels/<label_name>',
    methods=['GET'],
)
def get_label(state_machine_name, label_name):
    """
    Get a label within a given state machine.

    Returns:
    - 200 Ok: if the label is exists.
    - 404 Not Found: if the state machine or label does not exist.

    Successful return codes return the full context for the label.
    """
    app = server.config.app
    label = Label(label_name, state_machine_name)

    try:
        context = state_machine.get_label_context(app, label)
    except UnknownLabel:
        abort(
            404,
            f"Label {label.name} in state machine '{label.state_machine}' "
            f"does not exist.",
        )
    return jsonify(context)


@server.route(
    '/state-machines/<state_machine_name>/labels/<label_name>',
    methods=['POST'],
)
def create_label(state_machine_name, label_name):
    """
    Create a label with a given context, and start it in the state machine.

    Returns:
    - 201 Created: if the label is successfully created and started.
    - 409 Conflict: if the label already exists in the state machine.
    - 404 Not Found: if the state machine does not exist.
    - 400 Bad Request: if the request body is not a valid context.

    Successful return codes return the full created context for the label.
    """
    app = server.config.app
    label = Label(label_name, state_machine_name)
    data = request.get_json()

    try:
        context = state_machine.create_label(app, label, data)
        return jsonify(context), 201
    except UnknownStateMachine:
        msg = f"State machine '{state_machine_name}' does not exist"
        raise abort(404, msg)


@server.route(
    '/state-machines/<state_machine_name>/labels/<label_name>/update', # noqa
    methods=['POST'],
)
def update_label(state_machine_name, label_name):
    """
    Update a label in a state machine.

    Triggering progression if necessary according to the state machine
    configuration. Updates are _merged_ with existing context.

    Returns:
    - 200 Ok: if the label is successfully updated.
    - 400 Bad Request: if the request body is not a valid context.
    - 404 Not Found: if the state machine or label does not exist.

    Successful return codes return the full new context for a label.
    """
    app = server.config.app
    label = Label(label_name, state_machine_name)

    try:
        new_context = state_machine.update_context_for_label(
            app,
            label,
            request.get_json(),
        )
        return jsonify(new_context)
    except (UnknownLabel, UnknownStateMachine):
        raise abort(
            404,
            f"Label {label_name} in state machine '{state_machine_name}' "
            f"does not exist.",
        )


@server.route(
    '/state-machines/<state_machine_name>/labels/<label_name>',
    methods=['DELETE'],
)
def delete_label(state_machine_name, label_name):
    """
    Delete a label in a state machine.

    Marks a label as deleted, but does not remove it from the database.
    Deleted labels cannot be updated and will not move state.

    Returns:
    - 204 No content: if the label is successfully deleted.
    - 404 Not Found: if the state machine or label does not exist.
    """
    pass
