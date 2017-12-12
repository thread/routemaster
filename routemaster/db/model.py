"""Database model definition."""
from typing import Any

from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base: Any = declarative_base()


class Label(Base):
    """The representation of the state of a label."""
    __tablename__ = 'labels'

    name = Column(String, primary_key=True)
    state_machine = Column(String, primary_key=True)

    context = Column(JSONB)


class History(Base):
    """Represents history of state transitions for a label."""
    __tablename__ = 'label_history'

    id = Column(Integer, primary_key=True, autoincrement=True)

    label_name = Column(String)
    label_state_machine = Column(String)

    __table_args__: Any = (
        ForeignKeyConstraint(
            [label_name, label_state_machine],
            [Label.name, Label.state_machine],
        ),
        {},
    )

    created = Column(DateTime)

    # `forced = True` represents a manual transition that may not be in
    # accordance with the state machine logic.
    forced = Column(Boolean, default=False)

    # Null indicates starting a state machine
    old_state = Column(String, nullable=True)
    new_state = Column(String)


class StateMachine(Base):
    """
    Represents a state machine.

    We serialise versions of the configuration into the database so that:
     - The structure of the state machines can be exported to a data warehouse.
     - We don't rely on stringly-typed fields in rest of the data model.
    """
    __tablename__ = 'state_machines'

    name = Column(String, primary_key=True)
    updated = Column(DateTime)


class State(Base):
    """Represents a state in a state machine."""
    __tablename__ = 'states'

    name = Column(String, primary_key=True)
    state_machine = Column(
        String,
        ForeignKey(StateMachine.name),
        primary_key=True,
    )

    # `deprecated = True` represents a state that is no longer accessible.
    deprecated = Column(Boolean, default=False)

    updated = Column(DateTime)
