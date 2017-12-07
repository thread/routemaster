"""Parser and compiler for exit conditions."""

from routemaster.exit_conditions.tokenizer import TokenKind, tokenize
from routemaster.exit_conditions.operations import Operation
from routemaster.exit_conditions.exceptions import ParseError


class _TokenSource(object):
    """A source of tokens in a form which is convenient for parsing."""

    def __init__(self, iterable):
        self.iterable = filter(
            lambda token: token.kind not in (
                TokenKind.COMMENT,
                TokenKind.WHITESPACE,
            ),
            iterable,
        )
        self.previous_location = None
        self.head = object()
        self._advance()

    def _advance(self):
        if self.head is None:
            return

        try:
            self.previous_location = getattr(self.head, 'location', None)
            self.head = next(self.iterable)
        except StopIteration:
            self.head = None

    def get_next(self, *kinds):
        if not self.peek_next(*kinds):
            return False

        self._advance()
        return True

    def peek_next(self, *kinds):
        if self.head is None:
            return False

        if self.head.kind in kinds:
            return True
        return False

    def eat_next(self, *kinds):
        if self.head is None:
            raise ParseError("Unexpected EOF", self.previous_location)

        if self.head.kind in kinds:
            old_head = self.head
            self._advance()
            return old_head
        raise ParseError("Expected {kind}, got {actual_kind}".format(
            kind=', '.join(str(x) for x in kinds),
            actual_kind=str(self.head.kind),
        ), self.head.location)


def _parse_and_expr(source):
    already_bool_converted = False

    yield from _parse_or_expr(source)

    while source.get_next(TokenKind.AND):
        if not already_bool_converted:
            already_bool_converted = True
            yield Operation.TO_BOOL,
        yield from _parse_or_expr(source)
        yield Operation.TO_BOOL,
        yield Operation.AND,


def _parse_or_expr(source):
    already_bool_converted = False

    yield from _parse_base_expr(source)

    while source.get_next(TokenKind.OR):
        if not already_bool_converted:
            already_bool_converted = True
            yield Operation.TO_BOOL,
        yield from _parse_base_expr(source)
        yield Operation.TO_BOOL,
        yield Operation.OR,


def _parse_base_expr(source):
    negated = False
    known_bool = False
    while source.get_next(TokenKind.NOT):
        negated = not negated

    yield from _parse_value(source)
    if source.get_next(TokenKind.COPULA):
        # `is` or `has` expression
        if source.get_next(TokenKind.NOT):
            negated = not negated

        adjective = source.eat_next(TokenKind.ATOM)
        yield Operation.PROPERTY, adjective.value

        known_bool = True

    elif source.peek_next(TokenKind.OPERATOR):
        try:
            operator, is_negative, known_bool = {
                '=': (Operation.EQ, False, True),
                '/=': (Operation.EQ, True, True),
                '<': (Operation.LT, False, True),
                '>': (Operation.GT, False, True),
                '<=': (Operation.GT, True, True),
                '>=': (Operation.LT, True, True),
            }[source.head.value]
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
        if not known_bool:
            yield TokenKind.TO_BOOL,
        yield TokenKind.NOT,


def _parse_value(source):
    # Immediate special-case: parentheticals
    if source.get_next(TokenKind.LEFT_PAREN):
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
    raise ParseError(
        "Expected a value, got {kind}".format(
            kind=str(source.head.kind),
        ),
        location=source.head.location,
    )


def _parse_tokens(token_stream):
    source = _TokenSource(token_stream)
    yield from _parse_and_expr(source)


def parse(source):
    """Compile from arbitrary source to a sequence of program instructions."""
    return tuple(_parse_tokens(tokenize(source)))
