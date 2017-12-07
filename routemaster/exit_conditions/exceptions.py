"""Exceptions for use in exit condition handling."""


class ParseError(Exception):
    """Errors that occur when tokenizing or parsing."""

    def __init__(self, message, location):
        """
        Construct by message and location.

        location is given as a 2-tuple of a start and end position in the
        source.
        """
        self.message = message
        self.location = location
