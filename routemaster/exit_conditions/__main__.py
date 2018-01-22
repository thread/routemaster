"""Entry point for debugging purposes."""

import sys

from routemaster.exit_conditions.parser import parse
from routemaster.exit_conditions.peephole import peephole_optimise
from routemaster.exit_conditions.exceptions import ParseError
from routemaster.exit_conditions.error_display import (
    format_parse_error_message,
)

source = sys.stdin.read()
try:
    for instruction, *args in peephole_optimise(parse(source)):
        sys.stdout.write(
            f"{instruction.value} {', '.join(repr(x) for x in args)}",
        )
except ParseError as e:
    sys.stdout.write(format_parse_error_message(
        source=source,
        error=e,
    ))
