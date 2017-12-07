"""Top-level utility for exit condition programs."""

from routemaster.exit_conditions.parser import parse
from routemaster.exit_conditions.analysis import find_accessed_keys
from routemaster.exit_conditions.evaluator import evaluate
from routemaster.exit_conditions.error_display import format_parse_error_message
from routemaster.exit_conditions.exceptions import ParseError


class _ProgramContext(object):
    def __init__(self, *, variables, time_elapsed):
        self.variables = variables
        self.time_elapsed = time_elapsed

    def lookup(self, key):
        return self.variables.get('.'.join(key))

    def property_handler(self, property_name, value):
        if tuple(property_name) == ('passed',):
            return self.time_elapsed > value
        raise ValueError("Unknown property {name}".format(
            name='.'.join(property_name)),
        )


class ExitConditionProgram(object):
    """Compiled exit condition program."""

    def __init__(self, source):
        """
        Construct from source.

        This will eagerly compile and report any errors.
        """
        try:
            self.instructions = list(parse(source))
        except ParseError as exc:
            raise ValueError(format_parse_error_message(
                source=source,
                error=exc,
            )) from None

    def accessed_variables(self):
        """Iterable of names of variables accessed in this program."""
        for accessed_key in find_accessed_keys(self.instructions):
            yield '.'.join(accessed_key)

    def run(self, variables, time_elapsed):
        """Evaluate this program with a given context."""
        context = _ProgramContext(
            variables=variables,
            time_elapsed=time_elapsed,
        )

        return evaluate(
            self.instructions,
            context.lookup,
            context.property_handler,
        )
