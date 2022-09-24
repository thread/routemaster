"""Exit condition program evaluator."""

import datetime
from typing import Any, Dict, List, Tuple, Union, Callable, Iterable

from routemaster.exit_conditions.operations import Operation
from routemaster.exit_conditions.prepositions import Preposition

Stack = List[Union[
    Any,
    bool,
    int,
    str,
    None,
    datetime.datetime,
    Tuple[int, int],
]]


def _evaluate_to_bool(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
) -> None:
    top_of_stack = stack.pop()
    stack.append(bool(top_of_stack))


def _evaluate_not(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
) -> None:
    top_of_stack = stack.pop()
    stack.append(not top_of_stack)


def _evaluate_and(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
) -> None:
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs and rhs)


def _evaluate_or(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
) -> None:
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs or rhs)


def _evaluate_literal(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
    value: Any,
) -> None:
    stack.append(value)


def _evaluate_lookup(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
    key: Tuple[str, ...],
) -> None:
    stack.append(lookup(key))


def _evaluate_eq(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
) -> None:
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs == rhs)


def _evaluate_lt(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
) -> None:
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs < rhs)  # type: ignore[operator]


def _evaluate_gt(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
) -> None:
    rhs = stack.pop()
    lhs = stack.pop()
    stack.append(lhs > rhs)  # type: ignore[operator]


def _evaluate_property(
    stack: Stack,
    lookup: Callable,
    property_handler: Callable,
    property_name: Tuple[str, ...],
    prepositions: Tuple[Preposition, ...],
) -> None:
    prepositional_arguments = {}
    for preposition in reversed(prepositions):
        prepositional_arguments[preposition.value] = stack.pop()
    subject = stack.pop()
    stack.append(
        property_handler(property_name, subject, **prepositional_arguments),
    )


EVALUATORS: Dict[Operation, Callable] = {
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


def evaluate(
    instructions: Iterable[Any],
    lookup: Callable,
    property_handler: Callable,
) -> bool:
    """
    Run the instructions given in `instructions`.

    Returns the single result.
    """
    stack: Stack = []
    for instruction, *args in instructions:
        EVALUATORS[instruction](stack, lookup, property_handler, *args)
    return stack.pop()  # type: ignore[return-value]
