"""Database model definition."""
import datetime
import functools

import dateutil.tz
from sqlalchemy import DDL, Table
from sqlalchemy import Column as NullableColumn
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    DateTime,
    MetaData,
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
                    NEW.updated = now() AT TIME ZONE 'UTC';
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
        DateTime(timezone=True),
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

    Column(
        'created',
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(dateutil.tz.tzutc()),
    ),

    # `forced = True` represents a manual transition that may not be in
    # accordance with the state machine logic.
    Column('forced', Boolean, default=False),

    # Null indicates starting a state machine
    NullableColumn('old_state', String),

    # Null indicates being deleted from a state machine
    NullableColumn('new_state', String),
)
