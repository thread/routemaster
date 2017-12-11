"""Exit condition program evaluator."""

from routemaster.exit_conditions.operations import Operation


def _evaluate_to_bool(stack, lookup, property_handler):
    top_of_stack = stack.pop()
    stack.append(bool(top_of_stack))


def _evaluate_not(stack, lookup, property_handler):
    top_of_stack = stack.pop()
    stack.append(not top_of_stack)


def _evaluate_and(stack, lookup, property_handler):
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs and rhs)


def _evaluate_or(stack, lookup, property_handler):
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs or rhs)


def _evaluate_literal(stack, lookup, property_handler, value):
    stack.append(value)


def _evaluate_lookup(stack, lookup, property_handler, key):
    stack.append(lookup(key))


def _evaluate_eq(stack, lookup, property_handler):
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs == rhs)


def _evaluate_lt(stack, lookup, property_handler):
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs < rhs)


def _evaluate_gt(stack, lookup, property_handler):
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs > rhs)


def _evaluate_property(
    stack,
    lookup,
    property_handler,
    property_name,
    prepositions,
):
    prepositional_arguments = {}
    for preposition in reversed(prepositions):
        prepositional_arguments[preposition.value] = stack.pop()
    subject = stack.pop()
    stack.append(
        property_handler(property_name, subject, **prepositional_arguments),
    )


EVALUATORS = {
    Operation.TO_BOOL: _evaluate_to_bool,
    Operation.AND: _evaluate_and,
    Operation.OR: _evaluate_or,
    Operation.NOT: _evaluate_not,
    Operation.PROPERTY: _evaluate_property,
    Operation.GT: _evaluate_gt,
    Operation.LT: _evaluate_lt,
    Operation.EQ: _evaluate_eq,
    Operation.LITERAL: _evaluate_literal,
    Operation.LOOKUP: _evaluate_lookup,
}


def evaluate(instructions, lookup, property_handler):
    """
    Run the instructions given in `instructions`.

    Returns the single result.
    """
    stack = []
    for instruction, *args in instructions:
        EVALUATORS[instruction](stack, lookup, property_handler, *args)
    return stack.pop()
