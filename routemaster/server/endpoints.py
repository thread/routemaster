"""Core API endpoints for routemaster service."""

from sanic import Sanic
from sanic.response import json as json_response
from sanic.exceptions import NotFound

from routemaster import state_machine
from routemaster.state_machine import Label, UnknownLabel, UnknownStateMachine

server = Sanic('routemaster')


@server.route('/', methods=['GET'])
def status(request):
    """Status check endpoint."""
    try:
        with server.config.app.db.begin() as conn:
            conn.execute('select 1')
            return json_response({'status': 'ok'})
    except Exception:
        return json_response({'status': 'Could not connect to database'})


@server.route(
    '/state-machines/<state_machine_name:string>/labels',
    methods=['GET'],
)
def get_labels(request, state_machine_name):
    """List the labels in a state machine."""
    pass


@server.route(
    '/state-machines/<state_machine_name:string>/labels/<label_name:string>',
    methods=['GET'],
)
def get_label(request, state_machine_name, label_name):
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
        raise NotFound(
            f"Label {label.name} in state machine '{label.state_machine}' "
            f"does not exist."
        )
    return json_response(context)


@server.route(
    '/state-machines/<state_machine_name:string>/labels/<label_name:string>',
    methods=['POST'],
)
def create_label(request, state_machine_name, label_name):
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

    try:
        context = state_machine.create_label(app, label, request.json)
        return json_response(context, status=201)
    except UnknownStateMachine:
        msg = f"State machine '{state_machine_name}' does not exist"
        raise NotFound(msg)


@server.route(
    '/state-machines/<state_machine_name:string>/labels/<label_name:string>/update', # noqa
    methods=['POST'],
)
def update_label(request, state_machine_name, label_name):
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
    label = Label(label_name, state_machine)

    try:
        new_context = state_machine.update_context_for_label(
            app,
            label,
            request.json,
        )
        return json_response(new_context, status=200)
    except UnknownLabel:
        raise NotFound(
            f"Label {label_name} in state machine '{state_machine_name}' "
            f"does not exist."
        )


@server.route(
    '/state-machines/<state_machine_name:string>/labels/<label_name:string>',
    methods=['DELETE'],
)
def delete_label(request, state_machine_name, label_name):
    """
    Delete a label in a state machine.

    Marks a label as deleted, but does not remove it from the database.
    Deleted labels cannot be updated and will not move state.

    Returns:
    - 204 No content: if the label is successfully deleted.
    - 404 Not Found: if the state machine or label does not exist.
    """
    pass
