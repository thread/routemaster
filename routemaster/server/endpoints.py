"""Core API endpoints for routemaster service."""

from sanic import Sanic
from sanic.response import json as json_response

from routemaster import app

server = Sanic('routemaster')


@server.route("/")
async def status(request):
    """Status check endpoint."""
    print(app)
    return json_response({'config': app.raw_config})
