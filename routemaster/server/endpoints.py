"""Core API endpoints for routemaster service."""

from sanic import Sanic
from sanic.response import json

from routemaster import app

server = Sanic('routemaster')


@server.route("/")
async def status(request):
    """Status check endpoint."""
    return json(app.raw_config)
