"""Database model definition."""
import datetime

from sqlalchemy import (
    Table,
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    MetaData,
    ForeignKey,
    ForeignKeyConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()


"""The representation of the state of a label."""
labels = Table(
    'labels',
    metadata,
    Column('name', String, primary_key=True),
    Column('state_machine', String, primary_key=True),
    Column('metadata', JSONB),
    Column('deleted', Boolean, default=False),
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
    Column('old_state', String, nullable=True),
    Column('new_state', String),

    # Can we get foreign key constraints on these as well?
    # Currently: no, because those columns are not unique themselves, however
    # we could add `old_state_state_machine` and `new_state_state_machine`, add
    # the constraints with them, and then add a constraint that the three
    # state machine references are all identical.
    # ForeignKeyConstraint(
    #     ['old_state'],
    #     ['states.name'],
    # ),
    # ForeignKeyConstraint(
    #     ['new_state'],
    #     ['states.name'],
    # ),
)


"""
Represents a state machine.

We serialise versions of the configuration into the database so that:
- The structure of the state machines can be exported to a data warehouse.
- We don't rely on stringly-typed fields in rest of the data model.
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
    Column('state_machine', String, primary_key=True, nullable=False),
    Column('from_state', String, primary_key=True, nullable=False),
    Column('to_state', String, primary_key=True, nullable=False),
    Column('deprecated', Boolean, default=False, nullable=False),
    Column('updated', DateTime, nullable=False),
    ForeignKeyConstraint(
        columns=('state_machine', 'from_state'),
        refcolumns=(states.c.state_machine, states.c.name),
    ),
    ForeignKeyConstraint(
        columns=('state_machine', 'to_state'),
        refcolumns=(states.c.state_machine, states.c.name),
    ),
)
