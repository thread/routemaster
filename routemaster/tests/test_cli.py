from click.testing import CliRunner

from routemaster.cli import main


def test_cli_with_no_config_fails(app_env):
    result = CliRunner(env=app_env).invoke(main, ['validate'])
    assert result.exit_code == 2


def test_cli_with_trivial_config(app_env):
    result = CliRunner(env=app_env).invoke(
        main, ['-c', 'test_data/trivial.yaml', 'validate'])
    assert result.exit_code == 0, result.output


def test_cli_with_invalid_config_fails(app_env):
    result = CliRunner(env=app_env).invoke(
        main, ['-c', 'test_data/disconnected.yaml', 'validate'])
    assert result.exit_code == 1, result.output


def test_cli_with_unloadable_config_fails(app_env):
    result = CliRunner(env=app_env).invoke(
        main, ['-c', 'test_data/not_yaml.json', 'validate'])
    assert result.exit_code == 1, result.output


def test_cli_with_invalid_config_cannot_serve(app_env):
    result = CliRunner(env=app_env).invoke(
        main, ['-c', 'test_data/disconnected.yaml', 'serve'])
    assert result.exit_code == 1, result.output
