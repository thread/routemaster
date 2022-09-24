"""Exceptions for use in exit condition handling."""
from typing import Tuple


class ParseError(Exception):
    """Errors that occur when tokenizing or parsing."""

    def __init__(self, message: str, location: Tuple[int, int]) -> None:
        """
        Construct by message and location.

        location is given as a 2-tuple of a start and end position in the
        source.
        """
        self.message = message
        self.location = location
