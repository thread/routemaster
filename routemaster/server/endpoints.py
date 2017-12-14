"""Core API endpoints for routemaster service."""

from sanic import Sanic
from sqlalchemy import and_
from sanic.response import json as json_response
from sqlalchemy.sql import select
from sanic.exceptions import NotFound

from routemaster.db import labels
from routemaster.utils import dict_merge

server = Sanic('routemaster')


@server.route('/', methods=['GET'])
async def status(request):
    """Status check endpoint."""
    async with server.config.app.db.begin() as conn:
        num_labels = await conn.scalar(labels.count())
        num_state_machines = len(server.config.app.config.state_machines)
        return json_response({
            'labels': num_labels,
            'state_machines': num_state_machines,
        })


@server.route(
    '/state-machines/<state_machine_name:string>/labels',
    methods=['GET'],
)
async def get_labels(request, state_machine_name):
    """List the labels in a state machine."""
    pass


@server.route(
    '/state-machines/<state_machine_name:string>/labels/<label_name:string>',
    methods=['GET'],
)
async def get_label(request, state_machine_name, label_name):
    """
    Get a label within a given state machine.

    Returns:
    - 200 Ok: if the label is exists.
    - 404 Not Found: if the state machine or label does not exist.

    Successful return codes return the full context for the label.
    """
    app = server.config.app

    async with app.db.begin() as conn:
        result = await conn.execute(
            select([labels.c.context]).where(and_(
                labels.c.name == label_name,
                labels.c.state_machine == state_machine_name,
            )),
        )
        context = await result.fetchone()
        if not context:
            raise NotFound(
                f"Label {label_name} in state machine '{state_machine_name}' "
                f"does not exist."
            )

        return json_response(context[labels.c.context], status=200)


@server.route(
    '/state-machines/<state_machine_name:string>/labels/<label_name:string>',
    methods=['POST'],
)
async def create_label(request, state_machine_name, label_name):
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

    try:
        state_machine = app.config.state_machines[state_machine_name]
    except KeyError as k:
        msg = f"State machine '{state_machine_name}' does not exist"
        raise NotFound(msg) from k

    async with app.db.begin() as conn:
        await conn.execute(labels.insert().values(
            name=label_name,
            state_machine=state_machine.name,
            context=request.json,
        ))
        return json_response(request.json, status=201)


@server.route(
    '/state-machines/<state_machine_name:string>/labels/<label_name:string>/update', # noqa
    methods=['POST'],
)
async def update_label(request, state_machine_name, label_name):
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

    context_field = labels.c.context
    label_filter = and_(
        labels.c.name == label_name,
        labels.c.state_machine == state_machine_name,
    )

    async with app.db.begin() as conn:
        result = await conn.execute(
            select([context_field]).where(label_filter),
        )
        existing_context = await result.fetchone()
        if not existing_context:
            raise NotFound(
                f"Label {label_name} in state machine '{state_machine_name}' "
                f"does not exist."
            )

        new_context = dict_merge(existing_context[context_field], request.json)

        await conn.execute(labels.update().where(label_filter).values(
            context=new_context,
        ))

        return json_response(new_context, status=200)


@server.route(
    '/state-machines/<state_machine_name:string>/labels/<label_name:string>',
    methods=['DELETE'],
)
async def delete_label(request, state_machine_name, label_name):
    """
    Delete a label in a state machine.

    Marks a label as deleted, but does not remove it from the database.
    Deleted labels cannot be updated and will not move state.

    Returns:
    - 204 No content: if the label is successfully deleted.
    - 404 Not Found: if the state machine or label does not exist.
    """
    pass
