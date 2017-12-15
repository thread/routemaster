"""Initialisation for database connections."""
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from routemaster.config import DatabaseConfig


def initialise_db(config: DatabaseConfig) -> Engine:
    """Initialise a database given the connection string."""
    engine = create_engine(config.connstr)
    return engine
