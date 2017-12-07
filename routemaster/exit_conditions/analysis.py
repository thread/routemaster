"""Analysis of compiled programs."""


from routemaster.exit_conditions.operations import Operation


def find_accessed_keys(instructions):
    """Yield each key accessed under the program."""
    for instruction, *args in instructions:
        if instruction == Operation.LOOKUP:
            yield args[0]
