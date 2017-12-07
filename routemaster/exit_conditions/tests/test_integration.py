import textwrap

import pytest

from routemaster.exit_conditions import ExitConditionProgram

PROGRAMS = [
    ("true", True, ()),
    ("false", False, ()),
    ("3 < 6", True, ()),
    ("foo = 5", False, ('foo',)),
    ("true and false", False, ()),
    ("false or true", True, ()),
    ("true and true and 3 = 3", True, ()),
    ("false or false or 3 > 5", False, ()),
    ("not true", False, ()),
    ("3h has passed", True, ()),
    ("not 4 >= 6", True, ()),
    ("3h has not passed", False, ()),
]


VARIABLES = {
    "foo": 4,
}

TIME_ELAPSED = 11200


@pytest.mark.parametrize("program, expected, variables", PROGRAMS)
def test_evaluate(program, expected, variables):
    program = ExitConditionProgram(program)
    assert program.run(VARIABLES, TIME_ELAPSED) == expected


@pytest.mark.parametrize("program, expected, variables", PROGRAMS)
def test_accessed_variables(program, expected, variables):
    program = ExitConditionProgram(program)
    assert sorted(program.accessed_variables()) == sorted(variables)


ERRORS = [
    (
        "(a = b",
        """
        Error on line 1: Unexpected EOF, expected RIGHT_PAREN
        (a = b
              ^
        """,
    ),
    (
        "a = b)",
        """
        Error on line 1: Unexpected token after end of program: RIGHT_PAREN
        a = b)
             ^
        """,
    ),
    (
        "a = ?",
        """
        Error on line 1: Expected a value, got OPERATOR
        a = ?
            ^
        """,
    ),
    (
        "a ** b",
        """
        Error on line 1: Unknown operator **
        a ** b
          ~~
        """,
    ),
]


@pytest.mark.parametrize("program, error", ERRORS)
def test_errors(program, error):
    with pytest.raises(ValueError) as compile_error:
        ExitConditionProgram(program)

    message = str(compile_error.value)

    assert textwrap.dedent(message).strip() == textwrap.dedent(error).strip()
