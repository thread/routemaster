"""Prepositions as used in property clauses."""

import enum


@enum.unique
class Preposition(enum.Enum):
    """Prepositions used in property clauses."""
    SINCE = 'since'
    IN = 'in'
