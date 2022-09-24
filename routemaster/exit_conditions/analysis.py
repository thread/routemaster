"""Analysis of compiled programs."""


from typing import Any, Tuple, Iterable, Iterator

from routemaster.exit_conditions.operations import Operation


def find_accessed_keys(
    instructions: Iterable[Any],
) -> Iterator[Tuple[str, ...]]:
    """Yield each key accessed under the program."""
    for instruction, *args in instructions:
        if instruction == Operation.LOOKUP:
            yield args[0]
