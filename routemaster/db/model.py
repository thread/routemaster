"""Database model definition."""
import datetime
import functools

from sqlalchemy import Column as NullableColumn
from sqlalchemy import (
    DDL,
    Table,
    String,
    Boolean,
    Integer,
    DateTime,
    MetaData,
    ForeignKey,
    FetchedValue,
    ForeignKeyConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

Column = functools.partial(NullableColumn, nullable=False)

sync_label_updated_column = DDL(
    '''
    CREATE OR REPLACE FUNCTION sync_label_updated_column_fn()
        RETURNS TRIGGER AS
            $$
                BEGIN
                    NEW.updated = now();
                    RETURN NEW;
                END;
            $$
        LANGUAGE PLPGSQL;

    CREATE TRIGGER sync_label_updated_column
        BEFORE UPDATE ON labels
        FOR EACH ROW
        EXECUTE PROCEDURE sync_label_updated_column_fn();
    ''',
)


"""The representation of the state of a label."""
labels = Table(
    'labels',
    metadata,
    Column('name', String, primary_key=True),
    Column('state_machine', String, primary_key=True),
    Column('metadata', JSONB),
    Column('metadata_triggers_processed', Boolean, default=True),
    Column('deleted', Boolean, default=False),
    Column(
        'updated',
        DateTime,
        server_default=func.now(),
        server_onupdate=FetchedValue(),
    ),
    listeners=[
        ('after_create', sync_label_updated_column),
    ],
)


"""Represents history of state transitions for a label."""
history = Table(
    'history',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),

    Column('label_name', String),
    Column('label_state_machine', String),
    ForeignKeyConstraint(
        ['label_name', 'label_state_machine'],
        ['labels.name', 'labels.state_machine'],
    ),

    Column('created', DateTime, default=datetime.datetime.utcnow),

    # `forced = True` represents a manual transition that may not be in
    # accordance with the state machine logic.
    Column('forced', Boolean, default=False),

    # Null indicates starting a state machine
    NullableColumn('old_state', String),
    NullableColumn('new_state', String),
)


"""
Represents a state machine.

We serialise versions of the configuration into the database so that the
structure of the state machines can be exported to a data warehouse.
"""
state_machines = Table(
    'state_machines',
    metadata,

    Column('name', String, primary_key=True),
    Column('updated', DateTime),
)


"""Represents a state in a state machine."""
states = Table(
    'states',
    metadata,
    Column('name', String, primary_key=True),
    Column(
        'state_machine',
        String,
        ForeignKey('state_machines.name'),
        primary_key=True,
    ),

    # `deprecated = True` represents a state that is no longer accessible.
    Column('deprecated', Boolean, default=False),

    Column('updated', DateTime),
)


"""Represents an edge between states in a state machine."""
edges = Table(
    'edges',
    metadata,
    Column('state_machine', String, primary_key=True),
    Column('from_state', String, primary_key=True),
    Column('to_state', String, primary_key=True),
    Column('deprecated', Boolean, default=False),
    Column('updated', DateTime),
    ForeignKeyConstraint(
        columns=('state_machine', 'from_state'),
        refcolumns=(states.c.state_machine, states.c.name),
    ),
    ForeignKeyConstraint(
        columns=('state_machine', 'to_state'),
        refcolumns=(states.c.state_machine, states.c.name),
    ),
)
