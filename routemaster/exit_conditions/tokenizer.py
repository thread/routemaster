"""Tokenization of exit condition programs."""

import re
import enum
import unicodedata
from typing import Any, Tuple, Iterable, NamedTuple

from routemaster.exit_conditions.exceptions import ParseError
from routemaster.exit_conditions.prepositions import Preposition

RE_DURATION = re.compile('^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$')


@enum.unique
class RawTokenKind(enum.Enum):
    """Types of (pre-digestion) program token."""
    LEFT_PAREN = 'LEFT_PAREN'
    RIGHT_PAREN = 'RIGHT_PAREN'
    ATOM = 'ATOM'
    OPERATOR = 'OPERATOR'
    COMMENT = 'COMMENT'
    WHITESPACE = 'WHITESPACE'


@enum.unique
class TokenKind(enum.Enum):
    """Types of major program token."""

    LEFT_PAREN = '"("'
    RIGHT_PAREN = '")"'
    ATOM = 'atom'
    OPERATOR = 'operator'
    NUMBER = 'number'
    DURATION = 'duration'
    AND = '"and"'
    OR = '"or"'
    NOT = '"not"'
    LITERAL = 'constant'
    COPULA = 'is/has'
    PREPOSITION = 'preposition'


RAW_TOKEN_KIND_TO_TOKEN_KIND = {
    RawTokenKind.LEFT_PAREN: TokenKind.LEFT_PAREN,
    RawTokenKind.RIGHT_PAREN: TokenKind.RIGHT_PAREN,
    RawTokenKind.OPERATOR: TokenKind.OPERATOR,
}


class RawToken(NamedTuple):
    """A single raw (in-text, undigested) token."""

    kind: RawTokenKind
    value: str
    location: Tuple[int, int]


class Token(NamedTuple):
    """A single digested (usable) token."""

    kind: TokenKind
    value: Any
    location: Tuple[int, int]


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
    (None, 'Ps('): RawTokenKind.LEFT_PAREN,
    (None, 'Pe)'): RawTokenKind.RIGHT_PAREN,
    (None, 'Z'): RawTokenKind.WHITESPACE,
    (None, 'Cc'): RawTokenKind.WHITESPACE,
    (None, 'Po#'): RawTokenKind.COMMENT,
    (None, 'L'): RawTokenKind.ATOM,
    (None, 'Pd'): RawTokenKind.ATOM,
    (None, 'Pc'): RawTokenKind.ATOM,
    (None, 'N'): RawTokenKind.ATOM,
    (None, 'S'): RawTokenKind.OPERATOR,
    (None, 'Po'): RawTokenKind.OPERATOR,
    (RawTokenKind.WHITESPACE, 'Ps('): RawTokenKind.LEFT_PAREN,
    (RawTokenKind.WHITESPACE, 'Pe)'): RawTokenKind.RIGHT_PAREN,
    (RawTokenKind.WHITESPACE, 'Z'): RawTokenKind.WHITESPACE,
    (RawTokenKind.WHITESPACE, 'Cc'): RawTokenKind.WHITESPACE,
    (RawTokenKind.WHITESPACE, 'Po#'): RawTokenKind.COMMENT,
    (RawTokenKind.WHITESPACE, 'L'): RawTokenKind.ATOM,
    (RawTokenKind.WHITESPACE, 'Pd'): RawTokenKind.ATOM,
    (RawTokenKind.WHITESPACE, 'Pc'): RawTokenKind.ATOM,
    (RawTokenKind.WHITESPACE, 'N'): RawTokenKind.ATOM,
    (RawTokenKind.WHITESPACE, 'S'): RawTokenKind.OPERATOR,
    (RawTokenKind.WHITESPACE, 'Po'): RawTokenKind.OPERATOR,
    (RawTokenKind.LEFT_PAREN, 'Ps('): RawTokenKind.LEFT_PAREN,
    (RawTokenKind.LEFT_PAREN, 'Pe)'): RawTokenKind.RIGHT_PAREN,
    (RawTokenKind.LEFT_PAREN, 'Z'): RawTokenKind.WHITESPACE,
    (RawTokenKind.LEFT_PAREN, 'Cc'): RawTokenKind.WHITESPACE,
    (RawTokenKind.LEFT_PAREN, 'Po#'): RawTokenKind.COMMENT,
    (RawTokenKind.LEFT_PAREN, 'L'): RawTokenKind.ATOM,
    (RawTokenKind.LEFT_PAREN, 'Pd'): RawTokenKind.ATOM,
    (RawTokenKind.LEFT_PAREN, 'Pc'): RawTokenKind.ATOM,
    (RawTokenKind.LEFT_PAREN, 'N'): RawTokenKind.ATOM,
    (RawTokenKind.LEFT_PAREN, 'S'): RawTokenKind.OPERATOR,
    (RawTokenKind.LEFT_PAREN, 'Po'): RawTokenKind.OPERATOR,
    (RawTokenKind.RIGHT_PAREN, 'Ps('): RawTokenKind.LEFT_PAREN,
    (RawTokenKind.RIGHT_PAREN, 'Pe)'): RawTokenKind.RIGHT_PAREN,
    (RawTokenKind.RIGHT_PAREN, 'Z'): RawTokenKind.WHITESPACE,
    (RawTokenKind.RIGHT_PAREN, 'Cc'): RawTokenKind.WHITESPACE,
    (RawTokenKind.RIGHT_PAREN, 'Po#'): RawTokenKind.COMMENT,
    (RawTokenKind.RIGHT_PAREN, 'L'): RawTokenKind.ATOM,
    (RawTokenKind.RIGHT_PAREN, 'Pd'): RawTokenKind.ATOM,
    (RawTokenKind.RIGHT_PAREN, 'Pc'): RawTokenKind.ATOM,
    (RawTokenKind.RIGHT_PAREN, 'N'): RawTokenKind.ATOM,
    (RawTokenKind.RIGHT_PAREN, 'S'): RawTokenKind.OPERATOR,
    (RawTokenKind.RIGHT_PAREN, 'Po'): RawTokenKind.OPERATOR,
    (RawTokenKind.COMMENT, 'Cc'): RawTokenKind.WHITESPACE,
    (RawTokenKind.COMMENT, 'L'): RawTokenKind.COMMENT,
    (RawTokenKind.COMMENT, 'N'): RawTokenKind.COMMENT,
    (RawTokenKind.COMMENT, 'P'): RawTokenKind.COMMENT,
    (RawTokenKind.COMMENT, 'S'): RawTokenKind.COMMENT,
    (RawTokenKind.COMMENT, 'Z'): RawTokenKind.COMMENT,
    (RawTokenKind.ATOM, 'Ps('): RawTokenKind.LEFT_PAREN,
    (RawTokenKind.ATOM, 'Pe)'): RawTokenKind.RIGHT_PAREN,
    (RawTokenKind.ATOM, 'Z'): RawTokenKind.WHITESPACE,
    (RawTokenKind.ATOM, 'Cc'): RawTokenKind.WHITESPACE,
    (RawTokenKind.ATOM, 'Po#'): RawTokenKind.COMMENT,
    (RawTokenKind.ATOM, 'L'): RawTokenKind.ATOM,
    (RawTokenKind.ATOM, 'Pd'): RawTokenKind.ATOM,
    (RawTokenKind.ATOM, 'Pc'): RawTokenKind.ATOM,
    (RawTokenKind.ATOM, 'N'): RawTokenKind.ATOM,
    (RawTokenKind.ATOM, 'S'): RawTokenKind.OPERATOR,
    (RawTokenKind.ATOM, 'Po'): RawTokenKind.ATOM,
    (RawTokenKind.OPERATOR, 'Ps('): RawTokenKind.LEFT_PAREN,
    (RawTokenKind.OPERATOR, 'Pe)'): RawTokenKind.RIGHT_PAREN,
    (RawTokenKind.OPERATOR, 'Z'): RawTokenKind.WHITESPACE,
    (RawTokenKind.OPERATOR, 'Cc'): RawTokenKind.WHITESPACE,
    (RawTokenKind.OPERATOR, 'Po#'): RawTokenKind.COMMENT,
    (RawTokenKind.OPERATOR, 'L'): RawTokenKind.ATOM,
    (RawTokenKind.OPERATOR, 'Pd'): RawTokenKind.ATOM,
    (RawTokenKind.OPERATOR, 'Pc'): RawTokenKind.ATOM,
    (RawTokenKind.OPERATOR, 'N'): RawTokenKind.ATOM,
    (RawTokenKind.OPERATOR, 'S'): RawTokenKind.OPERATOR,
    (RawTokenKind.OPERATOR, 'Po'): RawTokenKind.OPERATOR,
}


def raw_tokenize(src: str) -> Iterable[RawToken]:
    """
    Split the string `src` into an iterable of `RawToken`s.

    The raw tokens are sufficient to completely reproduce the input stream and
    so may be useful for editing applications, most users will probably want
    `tokenize`.
    """
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
                assert state is not None

                yield RawToken(
                    kind=state,
                    value=src[start:index],
                    location=(start, index),
                )
            start = index
            state = next_state

    if start != len(src):
        assert state is not None

        yield RawToken(
            kind=state,
            value=src[start:],
            location=(start, index + 1),
        )


def _digest_atom(raw_token: RawToken) -> Token:
    """Turn a raw `Atom` token into the more specific kinds."""

    # Is this a preposition
    try:
        return Token(
            kind=TokenKind.PREPOSITION,
            value=Preposition(raw_token.value),
            location=raw_token.location,
        )
    except ValueError:
        pass

    # Is this an integer value?
    try:
        return Token(
            kind=TokenKind.NUMBER,
            value=int(raw_token.value),
            location=raw_token.location,
        )
    except ValueError:
        pass

    # A float?
    try:
        return Token(
            kind=TokenKind.NUMBER,
            value=float(raw_token.value),
            location=raw_token.location,
        )
    except ValueError:
        pass

    # A duration?
    duration_match = RE_DURATION.match(raw_token.value)
    if duration_match is not None:
        total_length = (
            int(duration_match.group(1) or '0') * 24 * 60 * 60 +
            int(duration_match.group(2) or '0') * 60 * 60 +
            int(duration_match.group(3) or '0') * 60 +
            int(duration_match.group(4) or '0')
        )
        return Token(
            kind=TokenKind.DURATION,
            value=total_length,
            location=raw_token.location,
        )

    # A literal?
    try:
        kind, value = LITERALS[raw_token.value]
        return Token(
            kind=kind,
            value=value,
            location=raw_token.location,
        )
    except KeyError:
        pass

    # Pass through, split by dots
    return Token(
        kind=TokenKind.ATOM,
        value=raw_token.value.split('.'),
        location=raw_token.location,
    )


def tokenize(src: str) -> Iterable[Token]:
    """Split the string `src` into an iterable of `Token`s."""
    for raw_token in raw_tokenize(src):
        if (
            raw_token.kind in (RawTokenKind.COMMENT, RawTokenKind.WHITESPACE)
        ):
            continue

        if raw_token.kind == RawTokenKind.ATOM:
            yield _digest_atom(raw_token)
        else:
            yield Token(
                kind=RAW_TOKEN_KIND_TO_TOKEN_KIND[raw_token.kind],
                value=raw_token.value,
                location=raw_token.location,
            )
