"""Initialisation for database connections."""
from sqlalchemy import create_engine
from sqlalchemy_aio import ASYNCIO_STRATEGY
from sqlalchemy.engine import Engine

from routemaster.config import DatabaseConfig


def initialise_db(config: DatabaseConfig, *, asyncio: bool = True) -> Engine:
    """Initialise a database given the connection string."""
    if asyncio:
        return create_engine(config.connstr, strategy=ASYNCIO_STRATEGY)
    else:
        return create_engine(config.connstr)
