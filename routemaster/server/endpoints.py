"""Core API endpoints for routemaster service."""

from sanic import Sanic
from sanic.response import json as json_response

server = Sanic('routemaster')


@server.route("/")
async def status(request):
    """Status check endpoint."""
    async with server.config.app.db.begin() as conn:
        num_labels = await conn.scalar('select count(*) from labels')
        num_state_machines = len(server.config.app.config.state_machines)
        return json_response({
            'labels': num_labels,
            'state_machines': num_state_machines,
        })
