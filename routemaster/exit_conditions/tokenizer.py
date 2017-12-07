"""Tokenization of exit condition programs."""

import re
import enum
import collections
import unicodedata

from routemaster.exit_conditions.exceptions import ParseError

RE_DURATION = re.compile('^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$')


@enum.unique
class TokenKind(enum.Enum):
    """Types of major program token."""

    LEFT_PAREN = 'LEFT_PAREN'
    RIGHT_PAREN = 'RIGHT_PAREN'
    ATOM = 'ATOM'
    OPERATOR = 'OPERATOR'
    COMMENT = 'COMMENT'
    WHITESPACE = 'WHITESPACE'
    NUMBER = 'NUMBER'
    DURATION = 'DURATION'
    AND = 'AND'
    OR = 'OR'
    NOT = 'NOT'
    LITERAL = 'LITERAL'
    COPULA = 'COPULA'


Token = collections.namedtuple('Token', 'kind value location')

LITERALS = {
    'true': (TokenKind.LITERAL, True),
    'false': (TokenKind.LITERAL, False),
    'null': (TokenKind.LITERAL, None),
    'and': (TokenKind.AND, None),
    'or': (TokenKind.OR, None),
    'not': (TokenKind.NOT, None),
    'is': (TokenKind.COPULA, 'is'),
    'has': (TokenKind.COPULA, 'has'),
    'was': (TokenKind.COPULA, 'was'),
}

STATE_MACHINE = {
    (None, 'Ps('): TokenKind.LEFT_PAREN,
    (None, 'Pe)'): TokenKind.RIGHT_PAREN,
    (None, 'Z'): TokenKind.WHITESPACE,
    (None, 'Cc'): TokenKind.WHITESPACE,
    (None, 'Po#'): TokenKind.COMMENT,
    (None, 'L'): TokenKind.ATOM,
    (None, 'Pd'): TokenKind.ATOM,
    (None, 'Pc'): TokenKind.ATOM,
    (None, 'N'): TokenKind.ATOM,
    (None, 'S'): TokenKind.OPERATOR,
    (None, 'Po'): TokenKind.OPERATOR,
    (TokenKind.WHITESPACE, 'Ps('): TokenKind.LEFT_PAREN,
    (TokenKind.WHITESPACE, 'Pe)'): TokenKind.RIGHT_PAREN,
    (TokenKind.WHITESPACE, 'Z'): TokenKind.WHITESPACE,
    (TokenKind.WHITESPACE, 'Cc'): TokenKind.WHITESPACE,
    (TokenKind.WHITESPACE, 'Po#'): TokenKind.COMMENT,
    (TokenKind.WHITESPACE, 'L'): TokenKind.ATOM,
    (TokenKind.WHITESPACE, 'Pd'): TokenKind.ATOM,
    (TokenKind.WHITESPACE, 'Pc'): TokenKind.ATOM,
    (TokenKind.WHITESPACE, 'N'): TokenKind.ATOM,
    (TokenKind.WHITESPACE, 'S'): TokenKind.OPERATOR,
    (TokenKind.WHITESPACE, 'Po'): TokenKind.OPERATOR,
    (TokenKind.LEFT_PAREN, 'Ps('): TokenKind.LEFT_PAREN,
    (TokenKind.LEFT_PAREN, 'Pe)'): TokenKind.RIGHT_PAREN,
    (TokenKind.LEFT_PAREN, 'Z'): TokenKind.WHITESPACE,
    (TokenKind.LEFT_PAREN, 'Cc'): TokenKind.WHITESPACE,
    (TokenKind.LEFT_PAREN, 'Po#'): TokenKind.COMMENT,
    (TokenKind.LEFT_PAREN, 'L'): TokenKind.ATOM,
    (TokenKind.LEFT_PAREN, 'Pd'): TokenKind.ATOM,
    (TokenKind.LEFT_PAREN, 'Pc'): TokenKind.ATOM,
    (TokenKind.LEFT_PAREN, 'N'): TokenKind.ATOM,
    (TokenKind.LEFT_PAREN, 'S'): TokenKind.OPERATOR,
    (TokenKind.LEFT_PAREN, 'Po'): TokenKind.OPERATOR,
    (TokenKind.RIGHT_PAREN, 'Ps('): TokenKind.LEFT_PAREN,
    (TokenKind.RIGHT_PAREN, 'Pe)'): TokenKind.RIGHT_PAREN,
    (TokenKind.RIGHT_PAREN, 'Z'): TokenKind.WHITESPACE,
    (TokenKind.RIGHT_PAREN, 'Cc'): TokenKind.WHITESPACE,
    (TokenKind.RIGHT_PAREN, 'Po#'): TokenKind.COMMENT,
    (TokenKind.RIGHT_PAREN, 'L'): TokenKind.ATOM,
    (TokenKind.RIGHT_PAREN, 'Pd'): TokenKind.ATOM,
    (TokenKind.RIGHT_PAREN, 'Pc'): TokenKind.ATOM,
    (TokenKind.RIGHT_PAREN, 'N'): TokenKind.ATOM,
    (TokenKind.RIGHT_PAREN, 'S'): TokenKind.OPERATOR,
    (TokenKind.RIGHT_PAREN, 'Po'): TokenKind.OPERATOR,
    (TokenKind.COMMENT, 'Cc'): TokenKind.WHITESPACE,
    (TokenKind.COMMENT, 'L'): TokenKind.COMMENT,
    (TokenKind.COMMENT, 'N'): TokenKind.COMMENT,
    (TokenKind.COMMENT, 'P'): TokenKind.COMMENT,
    (TokenKind.COMMENT, 'S'): TokenKind.COMMENT,
    (TokenKind.COMMENT, 'Z'): TokenKind.COMMENT,
    (TokenKind.ATOM, 'Ps('): TokenKind.LEFT_PAREN,
    (TokenKind.ATOM, 'Pe)'): TokenKind.RIGHT_PAREN,
    (TokenKind.ATOM, 'Z'): TokenKind.WHITESPACE,
    (TokenKind.ATOM, 'Cc'): TokenKind.WHITESPACE,
    (TokenKind.ATOM, 'Po#'): TokenKind.COMMENT,
    (TokenKind.ATOM, 'L'): TokenKind.ATOM,
    (TokenKind.ATOM, 'Pd'): TokenKind.ATOM,
    (TokenKind.ATOM, 'Pc'): TokenKind.ATOM,
    (TokenKind.ATOM, 'N'): TokenKind.ATOM,
    (TokenKind.ATOM, 'S'): TokenKind.OPERATOR,
    (TokenKind.ATOM, 'Po'): TokenKind.ATOM,
    (TokenKind.OPERATOR, 'Ps('): TokenKind.LEFT_PAREN,
    (TokenKind.OPERATOR, 'Pe)'): TokenKind.RIGHT_PAREN,
    (TokenKind.OPERATOR, 'Z'): TokenKind.WHITESPACE,
    (TokenKind.OPERATOR, 'Cc'): TokenKind.WHITESPACE,
    (TokenKind.OPERATOR, 'Po#'): TokenKind.COMMENT,
    (TokenKind.OPERATOR, 'L'): TokenKind.ATOM,
    (TokenKind.OPERATOR, 'Pd'): TokenKind.ATOM,
    (TokenKind.OPERATOR, 'Pc'): TokenKind.ATOM,
    (TokenKind.OPERATOR, 'N'): TokenKind.ATOM,
    (TokenKind.OPERATOR, 'S'): TokenKind.OPERATOR,
    (TokenKind.OPERATOR, 'Po'): TokenKind.OPERATOR,
}


def _raw_tokenize(src):
    # Raw token handling; there is a later semantic mapping stage which
    # annotates atoms for the special handling of keywords and numbers.
    # We treat tokenization as an explicit state machine.
    # State transitions emit the previous block along with the previous state.
    state, start = None, 0

    for index, character in enumerate(src):
        next_state = None
        major_category = unicodedata.category(character) + character

        for (from_state, category_match), to_state in STATE_MACHINE.items():
            if (
                from_state == state and
                major_category.startswith(category_match)
            ):
                next_state = to_state
                break

        if next_state is None:
            raise ParseError(
                "Unexpected '{0!r}'".format(character),
                (index, index + 1),
            )

        if next_state != state:
            if start != index:
                yield Token(
                    kind=state,
                    value=src[start:index],
                    location=(start, index),
                )
            start = index
            state = next_state

    if start != len(src):
        yield Token(
            kind=state,
            value=src[start:],
            location=(start, index + 1),
        )


def _unscramble_atom(token):
    """Turn a general `Atom` token into the more specific kinds."""

    # Is this an integer value?
    try:
        return token._replace(
            kind=TokenKind.NUMBER,
            value=int(token.value),
        )
    except ValueError:
        pass

    # A float?
    try:
        return token._replace(
            kind=TokenKind.NUMBER,
            value=float(token.value),
        )
    except ValueError:
        pass

    # A duration?
    duration_match = RE_DURATION.match(token.value)
    if duration_match is not None:
        total_length = (
            int(duration_match.group(1) or '0') * 24 * 60 * 60 +
            int(duration_match.group(2) or '0') * 60 * 60 +
            int(duration_match.group(3) or '0') * 60 +
            int(duration_match.group(4) or '0')
        )
        return token._replace(
            kind=TokenKind.DURATION,
            value=total_length,
        )

    # A literal?
    try:
        kind, value = LITERALS[token.value]
        return token._replace(
            kind=kind,
            value=value,
        )
    except KeyError:
        pass

    # Pass through, split by dots
    return token._replace(
        value=token.value.split('.'),
    )


def tokenize(src, drop_whitespace=True):
    """Split the string `src` into an iterable of `Token`s."""
    for token in _raw_tokenize(src):
        if (
            token.kind in (TokenKind.COMMENT, TokenKind.WHITESPACE) and
            drop_whitespace
        ):
            continue

        if token.kind == TokenKind.ATOM:
            yield _unscramble_atom(token)
        else:
            yield token
