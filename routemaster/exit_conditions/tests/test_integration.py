import textwrap
import datetime
import dateutil.tz

import pytest

from routemaster.exit_conditions import Context, ExitConditionProgram

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
    ("3h has passed since old_time", True, ('old_time',)),
    ("not 4 >= 6", True, ()),
    ("3h has not passed since old_time", False, ('old_time',)),
    ("foo is defined", True, ('foo',)),
    ("bar is defined", False, ('bar',)),
    ("null is not defined", True, ()),
    ("(1 < 2) and (2 < foo)", True, ('foo',)),
    ("3 is not in objects", True, ('objects',)),
]


NOW = datetime.datetime(2017, 1, 1, 12, 0, 0, tzinfo=dateutil.tz.tzutc())
VARIABLES = {
    'foo': 4,
    'objects': (2, 4),
    'old_time': NOW - datetime.timedelta(hours=4),
}



@pytest.mark.parametrize("program, expected, variables", PROGRAMS)
def test_evaluate(program, expected, variables):
    program = ExitConditionProgram(program)
    assert program.run(Context(VARIABLES), NOW) == expected


@pytest.mark.parametrize("program, expected, variables", PROGRAMS)
def test_accessed_variables(program, expected, variables):
    program = ExitConditionProgram(program)
    assert sorted(program.accessed_variables()) == sorted(variables)


ERRORS = [
    (
        "(a = b",
        """
        Error on line 1: Unexpected EOF, expected ")"
        (a = b
              ^
        """,
    ),
    (
        "a = b)",
        """
        Error on line 1: Unexpected token after end of program: ")"
        a = b)
             ^
        """,
    ),
    (
        "a = ?",
        """
        Error on line 1: Expected a value, got operator
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
    (
        "a is ftaghn",
        """
        Unknown property ftaghn
        """,
    ),
    (
        "",
        """
        Error on line 1: Expected a value but this program is empty

        ^
        """,
    ),
    (
        "# hats",
        """
        Error on line 1: Expected a value but this program is empty
        # hats
        ^
        """,
    ),
    (
        "\na == b",
        """
        Error on line 2: Unknown operator == (did you mean =?)
        a == b
          ~~
        """,
    ),
    (
        "this is",
        """
        Error on line 1: Expected an adjective or preposition afterwards, but got the EOF
        this is
             ~~
        """,
    ),
    (
        "this is and",
        """
        Error on line 1: Expected an adjective or preposition
        this is and
                ~~~
        """,
    ),
]


@pytest.mark.parametrize("program, error", ERRORS)
def test_errors(program, error):
    with pytest.raises(ValueError) as compile_error:
        ExitConditionProgram(program).run(Context(VARIABLES), NOW)

    message = str(compile_error.value)

    assert textwrap.dedent(message).strip() == textwrap.dedent(error).strip()
