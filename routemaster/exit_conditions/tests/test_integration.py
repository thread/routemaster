import datetime
import textwrap

import pytest
import dateutil.tz

from routemaster.context import Context
from routemaster.exit_conditions import ExitConditionProgram

PROGRAMS = [
    ("true", True, ()),
    ("false", False, ()),
    ("3 < 6", True, ()),
    ("metadata.foo = 5", False, ('metadata.foo',)),
    ("true and false", False, ()),
    ("false or true", True, ()),
    ("true and true and 3 = 3", True, ()),
    ("false or false or 3 > 5", False, ()),
    ("not true", False, ()),
    ("3h has passed since metadata.old_time", True, ('metadata.old_time',)),
    ("not 4 >= 6", True, ()),
    ("3h has not passed since metadata.old_time", False, ('metadata.old_time',)),
    ("metadata.foo is defined", True, ('metadata.foo',)),
    ("metadata.bar is defined", False, ('metadata.bar',)),
    ("null is not defined", True, ()),
    ("(1 < 2) and (2 < metadata.foo)", True, ('metadata.foo',)),
    ("3 is not in metadata.objects", True, ('metadata.objects',)),
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
    context = Context(
        label='label1',
        metadata=VARIABLES,
        now=NOW,
        accessed_variables=program.accessed_variables(),
    )
    assert program.run(context) == expected


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
        "metadata.foo is ftaghn",
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


@pytest.mark.parametrize("source, error", ERRORS)
def test_errors(source, error):
    with pytest.raises(ValueError) as compile_error:
        program = ExitConditionProgram(source)
        context = Context(
            label='label1',
            metadata=VARIABLES,
            now=NOW,
            accessed_variables=program.accessed_variables(),
        )
        program.run(context)

    message = str(compile_error.value)

    assert textwrap.dedent(message).strip() == textwrap.dedent(error).strip()
