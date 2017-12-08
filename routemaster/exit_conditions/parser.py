"""Parser and compiler for exit conditions."""

from routemaster.exit_conditions.tokenizer import TokenKind, tokenize
from routemaster.exit_conditions.exceptions import ParseError
from routemaster.exit_conditions.operations import Operation

OPERATOR_DID_YOU_MEAN = {
    '==': '=',
    '!=': '/=',
    '<>': '/=',
}


class _TokenSource(object):
    """A source of tokens in a form which is convenient for parsing."""

    def __init__(self, iterable):
        self.iterable = iterable
        self.previous_location = None
        self.head = object()
        self._advance()

    def _advance(self):
        assert self.head is not None

        try:
            self.previous_location = getattr(self.head, 'location', None)
            self.head = next(self.iterable)
        except StopIteration:
            self.head = None

    def try_eat_next(self, *kinds):
        if not self.match_next(*kinds):
            return False

        self._advance()
        return True

    def match_next(self, *kinds):
        if self.head is None:
            return False

        if self.head.kind in kinds:
            return True
        return False

    def eat_next(self, *kinds):
        if self.head is None:
            if self.previous_location is None:
                # Empty program
                raise ParseError(
                    "Surprisingly, program was empty",
                    location=(0, 1),
                )

            end_of_last_location = self.previous_location[-1]
            raise ParseError(
                "Unexpected EOF, expected {kind}".format(
                    kind=', '.join(x.value for x in kinds),
                ),
                location=(
                    end_of_last_location,
                    end_of_last_location + 1,
                ),
            )

        if self.head.kind in kinds:
            old_head = self.head
            self._advance()
            return old_head
        raise ParseError("Expected {kind}, got {actual_kind}".format(
            kind=', '.join(x.value for x in kinds),
            actual_kind=self.head.kind.value,
        ), self.head.location)


def _parse_and_expr(source):
    already_bool_converted = False

    yield from _parse_or_expr(source)

    while source.try_eat_next(TokenKind.AND):
        if not already_bool_converted:
            already_bool_converted = True
            yield Operation.TO_BOOL,
        yield from _parse_or_expr(source)
        yield Operation.TO_BOOL,
        yield Operation.AND,


def _parse_or_expr(source):
    already_bool_converted = False

    yield from _parse_base_expr(source)

    while source.try_eat_next(TokenKind.OR):
        if not already_bool_converted:
            already_bool_converted = True
            yield Operation.TO_BOOL,
        yield from _parse_base_expr(source)
        yield Operation.TO_BOOL,
        yield Operation.OR,


def _parse_base_expr(source):
    negated = False
    while source.try_eat_next(TokenKind.NOT):
        negated = not negated

    yield from _parse_value(source)
    if source.try_eat_next(TokenKind.COPULA):
        # `is` or `has` expression
        if source.try_eat_next(TokenKind.NOT):
            negated = not negated

        try:
            adjective = tuple(source.eat_next(TokenKind.ATOM).value)
        except ParseError:
            # Must be a prepositional phrase
            adjective = ()

        prepositions = []
        while source.match_next(TokenKind.PREPOSITION):
            prepositions.append(source.head.value)
            source.eat_next(TokenKind.PREPOSITION)
            yield from _parse_value(source)

        if not adjective and not prepositions:
            if source.head is not None:
                raise ParseError(
                    "Expected an adjective or preposition",
                    source.head.location,
                )
            else:
                raise ParseError(
                    "Expected an adjective or preposition afterwards, "
                    "but got the EOF",
                    source.previous_location,
                )

        yield Operation.PROPERTY, tuple(adjective), tuple(prepositions)

    elif source.match_next(TokenKind.OPERATOR):
        try:
            operator, is_negative = {
                '=': (Operation.EQ, False),
                '/=': (Operation.EQ, True),
                '<': (Operation.LT, False),
                '>': (Operation.GT, False),
                '<=': (Operation.GT, True),
                '>=': (Operation.LT, True),
            }[source.head.value]
        except KeyError:
            try:
                suggested_replacement = \
                    OPERATOR_DID_YOU_MEAN[source.head.value]
                raise ParseError(
                    "Unknown operator {operator} "
                    "(did you mean {suggestion}?)".format(
                        operator=source.head.value,
                        suggestion=suggested_replacement,
                    ),
                    location=source.head.location,
                ) from None
            except KeyError:
                raise ParseError(
                    "Unknown operator {operator}".format(
                        operator=source.head.value,
                    ),
                    location=source.head.location,
                ) from None

        if is_negative:
            negated = not negated
        source.eat_next(TokenKind.OPERATOR)

        yield from _parse_value(source)
        yield operator,

    if negated:
        yield Operation.TO_BOOL,
        yield Operation.NOT,


def _parse_value(source):
    # Immediate special-case: parentheticals
    if source.try_eat_next(TokenKind.LEFT_PAREN):
        yield from _parse_and_expr(source)
        source.eat_next(TokenKind.RIGHT_PAREN)
        return

    # Atomic lookup
    try:
        atom = source.eat_next(TokenKind.ATOM)
        yield Operation.LOOKUP, tuple(atom.value)
        return
    except ParseError:
        pass

    # Literals
    try:
        literal = source.eat_next(TokenKind.LITERAL)
        yield Operation.LITERAL, literal.value
        return
    except ParseError:
        pass

    # Durations
    try:
        duration = source.eat_next(TokenKind.DURATION)
        yield Operation.LITERAL, duration.value
        return
    except ParseError:
        pass

    # Numbers
    try:
        number = source.eat_next(TokenKind.NUMBER)
        yield Operation.LITERAL, number.value
        return
    except ParseError:
        pass

    # No match
    if source.head is not None:
        raise ParseError(
            "Expected a value, got {kind}".format(
                kind=source.head.kind.value,
            ),
            location=source.head.location,
        )
    else:
        if source.previous_location is not None:
            raise ParseError(
                "Expected a value, but the EOF was reached",
                location=source.previous_location,
            )
        else:
            raise ParseError(
                "Expected a value but this program is empty",
                location=(0, 1),
            )


def _parse_tokens(token_stream):
    source = _TokenSource(token_stream)
    yield from _parse_and_expr(source)
    # Always end in a final TO_BOOL
    yield Operation.TO_BOOL,

    # Verify that this is actually the entire stream
    if source.head is not None:
        raise ParseError(
            f"Unexpected token after end of program: {source.head.kind.value}",
            location=source.head.location,
        )


def parse(source):
    """Compile from arbitrary source to a sequence of program instructions."""
    return tuple(_parse_tokens(tokenize(source)))
