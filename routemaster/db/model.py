"""Database model definition."""
from typing import Any

from sqlalchemy import Column, String, Integer, DateTime, ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

Base: Any = declarative_base()


class Label(Base):
    """The representation of the state of a label."""
    __tablename__ = 'labels'

    name = Column(String, primary_key=True)
    state_machine = Column(String, primary_key=True)

    state = Column(String)

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

    # Null indicates starting a state machine
    old_state = Column(String, nullable=True)
    new_state = Column(String)
