import pytest

from routemaster.exit_conditions.tokenizer import Token, TokenKind, tokenize
from routemaster.exit_conditions.exceptions import ParseError


def test_tokenize_empty():
    assert list(tokenize('')) == []


def test_tokenize_exhaustive():
    source = """
        jacquard.has_redesigned_first_two_drip_emails is defined and
        (recs.has_first_recommendations or 12h has passed) and
        foo > 1 and not bar and baz == null
    """
    expected = [
        Token(kind=TokenKind.ATOM, value=['jacquard', 'has_redesigned_first_two_drip_emails'], location=(9, 54)),
        Token(kind=TokenKind.COPULA, value='is', location=(55, 57)),
        Token(kind=TokenKind.ATOM, value=['defined'], location=(58, 65)),
        Token(kind=TokenKind.AND, value=None, location=(66, 69)),
        Token(kind=TokenKind.LEFT_PAREN, value='(', location=(78, 79)),
        Token(kind=TokenKind.ATOM, value=['recs', 'has_first_recommendations'], location=(79, 109)),
        Token(kind=TokenKind.OR, value=None, location=(110, 112)),
        Token(kind=TokenKind.DURATION, value=43200, location=(113, 116)),
        Token(kind=TokenKind.COPULA, value='has', location=(117, 120)),
        Token(kind=TokenKind.ATOM, value=['passed'], location=(121, 127)),
        Token(kind=TokenKind.RIGHT_PAREN, value=')', location=(127, 128)),
        Token(kind=TokenKind.AND, value=None, location=(129, 132)),
        Token(kind=TokenKind.ATOM, value=['foo'], location=(141, 144)),
        Token(kind=TokenKind.OPERATOR, value='>', location=(145, 146)),
        Token(kind=TokenKind.NUMBER, value=1, location=(147, 148)),
        Token(kind=TokenKind.AND, value=None, location=(149, 152)),
        Token(kind=TokenKind.NOT, value=None, location=(153, 156)),
        Token(kind=TokenKind.ATOM, value=['bar'], location=(157, 160)),
        Token(kind=TokenKind.AND, value=None, location=(161, 164)),
        Token(kind=TokenKind.ATOM, value=['baz'], location=(165, 168)),
        Token(kind=TokenKind.OPERATOR, value='==', location=(169, 171)),
        Token(kind=TokenKind.LITERAL, value=None, location=(172, 176)),
    ]
    assert list(tokenize(source)) == expected


def test_parse_error_on_invalid_characters():
    with pytest.raises(ParseError):
        print(list(tokenize("abc]")))
