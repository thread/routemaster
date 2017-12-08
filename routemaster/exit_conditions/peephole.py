"""Peephole evaluator optimiser."""

from routemaster.exit_conditions.operations import Operation

MATCHERS = [
    (
        [
            (Operation.NOT,),
            (Operation.NOT,),
        ],
        [
        ],
    ),
    (
        [
            (Operation.TO_BOOL,),
            (Operation.TO_BOOL,),
        ],
        [
            (Operation.TO_BOOL,),
        ],
    ),
    (
        [
            (Operation.NOT,),
            (Operation.TO_BOOL,),
        ],
        [
            (Operation.NOT,),
        ],
    ),
    (
        [
            (Operation.AND,),
            (Operation.TO_BOOL,),
        ],
        [
            (Operation.AND,),
        ],
    ),
    (
        [
            (Operation.OR,),
            (Operation.TO_BOOL,),
        ],
        [
            (Operation.OR,),
        ],
    ),
    (
        [
            (Operation.EQ,),
            (Operation.TO_BOOL,),
        ],
        [
            (Operation.EQ,),
        ],
    ),
    (
        [
            (Operation.LT,),
            (Operation.TO_BOOL,),
        ],
        [
            (Operation.LT,),
        ],
    ),
    (
        [
            (Operation.GT,),
            (Operation.TO_BOOL,),
        ],
        [
            (Operation.GT,),
        ],
    ),
]


def peephole_optimise(instructions):
    """Run peephole optimisations over a given instruction sequence."""
    instructions = list(instructions)

    any_changes = True

    while any_changes:
        any_changes = False

        for match_pattern, replace_pattern in MATCHERS:
            match_pattern_length = len(match_pattern)
            for index in range(len(instructions) + 1 - match_pattern_length):
                if (
                    instructions[index:index + match_pattern_length] ==
                    match_pattern
                ):
                    instructions[index:index + match_pattern_length] = \
                        replace_pattern
                    any_changes = True
                    break

        # TO_BOOL after property elimination
        for index in range(len(instructions) - 1):
            if (
                instructions[index][0] == Operation.PROPERTY and
                instructions[index + 1][0] == Operation.TO_BOOL
            ):
                del instructions[index + 1]
                any_changes = True
                break

    return instructions
