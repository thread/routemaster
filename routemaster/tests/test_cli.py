import contextlib

import pytest

from routemaster.cli import main


@contextlib.contextmanager
def clean_exit():
    with pytest.raises(SystemExit) as excinfo:
        yield

    exit_code = excinfo.value.code
    assert exit_code == 0


def test_cli_with_no_config_fails():
    with pytest.raises(SystemExit) as excinfo:
        main(['validate'])

    exit_code = excinfo.value.code
    assert exit_code == 2


def test_cli_with_trivial_config():
    with clean_exit():
        main(['-c', 'test_data/trivial.yaml', 'validate'])
