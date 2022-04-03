"""Database model definition."""
import datetime
import functools
from typing import Any

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
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

Base: Any  # Workaround for https://github.com/python/mypy/issues/2477
Base = declarative_base(metadata=metadata)

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


# ORM classes


class Label(Base):
    """A single label including context."""

    # Note: type annotations for this class are provided by a stubs file

    __table__ = Table(
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

    def __repr__(self):
        """Return a useful debug representation."""
        return (
            f"Label(state_machine={self.state_machine!r}, name={self.name!r})"
        )


class History(Base):
    """A single historical state transition of a label."""

    # Note: type annotations for this class are provided by a stubs file

    __table__ = Table(
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

    label = relationship(Label, backref='history')

    def __repr__(self):
        """Return a useful debug representation."""
        return (
            f"History(id={self.id!r}, "
            f"label_state_machine={self.label_state_machine!r}, "
            f"label_name={self.label_name!r})"
        )
