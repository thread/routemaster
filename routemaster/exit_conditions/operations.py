"""Operation definitions for the condition stack machine."""

import enum


@enum.unique
class Operation(enum.Enum):
    """Classes of instructions for the exit condition machine."""

    # Pop `value` from the stack, interpret it as a boolean, and push
    # that to the stack.
    TO_BOOL = 'to_bool'

    # Pop boolean `value` from the stack, negate it, and push the negated
    # form to the stack.
    NOT = 'not'

    # Pop boolean `rhs` and `lhs` from the stack, AND together, and push
    # that to the stack.
    AND = 'and'

    # Pop boolean `rhs` and `lhs` from the stack, OR together, and push
    # that to the stack.
    OR = 'or'

    # Push literal value `argument` to the stack.
    LITERAL = 'literal'

    # Look up symbol `argument` and push it to the stack, or None if not found.
    LOOKUP = 'lookup'

    # Pop boolean `rhs` and `lhs` from the stack, compare equality, and push
    # `true` if equal and `false` if not.
    EQ = 'eq'

    # Pop boolean `rhs` and `lhs` from the stack, compare ordering, and push
    # `true` if `rhs` is less than `lhs` and `false` if not.
    LT = 'lt'

    # Pop boolean `rhs` and `lhs` from the stack, compare ordering, and push
    # `true` if `rhs` is greater than `lhs` and `false` if not.
    GT = 'gt'

    # Pop value `value` from the stack, establish if it matches condition
    # `argument` and push `true` if so, `false` if not.
    PROPERTY = 'property'
