"""Core API endpoints for routemaster service."""

from sanic import Sanic
from sanic.response import json as json_response

server = Sanic('routemaster')


@server.route("/")
async def status(request):
    """Status check endpoint."""
    return json_response({'config': server.config.app.raw_config})
