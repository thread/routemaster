from routemaster.exit_conditions.program import ExitConditionProgram


def test_program_equality():
    assert ExitConditionProgram('true') == ExitConditionProgram('true')
    assert ExitConditionProgram('true') != ExitConditionProgram('false')
    assert ExitConditionProgram('true') != 'true'


def test_program_hash():
    assert hash(ExitConditionProgram('true')) == hash(ExitConditionProgram('true'))
    assert hash(ExitConditionProgram('true')) != hash(ExitConditionProgram('false'))
