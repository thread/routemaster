"""Top-level utility for exit condition programs."""

import typing

from routemaster.exit_conditions.parser import parse
from routemaster.exit_conditions.analysis import find_accessed_keys
from routemaster.exit_conditions.evaluator import evaluate
from routemaster.exit_conditions.exceptions import ParseError
from routemaster.exit_conditions.error_display import \
    format_parse_error_message


class _ProgramContext(object):
    def __init__(self, *, variables, time_elapsed):
        self.variables = variables
        self.time_elapsed = time_elapsed

    def lookup(self, key):
        return self.variables.get('.'.join(key))

    def property_handler(self, property_name, value):
        if tuple(property_name) == ('passed',):
            return self.time_elapsed > value
        if tuple(property_name) == ('defined',):
            return value is not None
        raise ValueError("Unknown property {name}".format(
            name='.'.join(property_name)),
        )


class ExitConditionProgram(object):
    """Compiled exit condition program."""

    def __init__(self, source: str) -> None:
        """
        Construct from source.

        This will eagerly compile and report any errors.
        """
        try:
            self._instructions = list(parse(source))
        except ParseError as exc:
            raise ValueError(format_parse_error_message(
                source=source,
                error=exc,
            )) from None

        self.source = source

    def accessed_variables(self) -> typing.Iterable[str]:
        """Iterable of names of variables accessed in this program."""
        for accessed_key in find_accessed_keys(self._instructions):
            yield '.'.join(accessed_key)

    def run(
        self,
        variables: typing.Mapping[str, typing.Any],
        time_elapsed: int,
    ) -> bool:
        """Evaluate this program with a given context."""
        context = _ProgramContext(
            variables=variables,
            time_elapsed=time_elapsed,
        )

        return evaluate(
            self._instructions,
            context.lookup,
            context.property_handler,
        )

    def __eq__(self, other_program: typing.Any) -> bool:
        if not isinstance(other_program, ExitConditionProgram):
            return False

        return other_program._instructions == self._instructions

    def __hash__(self) -> int:
        return hash(self._instructions)

    def __repr__(self):
        return f"{type(self).__name__}({self.source!r})"
