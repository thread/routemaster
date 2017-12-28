from click.testing import CliRunner

from routemaster.cli import main

runner = CliRunner()


def test_cli_with_no_config_fails():
    result = runner.invoke(main, ['validate'])
    assert result.exit_code == 2


def test_cli_with_trivial_config():
    result = runner.invoke(main, ['-c', 'test_data/trivial.yaml', 'validate'])
    assert result.exit_code == 0, result.output


def test_cli_with_invalid_config_fails():
    result = runner.invoke(main, ['-c', 'test_data/disconnected.yaml', 'validate'])
    assert result.exit_code == 1, result.output


def test_cli_with_invalid_config_cannot_serve():
    result = runner.invoke(main, ['-c', 'test_data/disconnected.yaml', 'serve'])
    assert result.exit_code == 1, result.output
