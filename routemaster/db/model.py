"""Database model definition."""
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
Label = Table(
    'labels',
    metadata,
    Column('name', String, primary_key=True),
    Column('state_machine', String, primary_key=True),
    Column('context', JSONB),
)


"""Represents history of state transitions for a label."""
History = Table(
    'label_history',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),

    Column('label_name', String),
    Column('label_state_machine', String),
    ForeignKeyConstraint(
        ['label_name', 'label_state_machine'],
        ['label.name', 'label.state_machine'],
    ),

    Column('created', DateTime),

    # `forced = True` represents a manual transition that may not be in
    # accordance with the state machine logic.
    Column('forced', Boolean, default=False),

    # Null indicates starting a state machine
    Column('old_state', String, nullable=True),
    Column('new_state', String),
    ForeignKeyConstraint(
        ['old_state'],
        ['states.name'],
    ),
    ForeignKeyConstraint(
        ['new_state'],
        ['states.name'],
    ),
)


"""
Represents a state machine.

We serialise versions of the configuration into the database so that:
- The structure of the state machines can be exported to a data warehouse.
- We don't rely on stringly-typed fields in rest of the data model.
"""
StateMachine = Table(
    'state_machines',
    metadata,

    Column('name', String, primary_key=True),
    Column('updated', DateTime),
)


"""Represents a state in a state machine."""
State = Table(
    'states',
    metadata,
    Column('name', String, primary_key=True),
    Column(
        'state_machine',
        String,
        ForeignKey(StateMachine.name),
        primary_key=True,
    ),

    # `deprecated = True` represents a state that is no longer accessible.
    Column('deprecated', Boolean, default=False),

    Column('updated', DateTime),
)
