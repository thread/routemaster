import pytest

from routemaster.config import DatabaseConfig

CASES = (
    (
        ('db', 5432, 'dbname', 'user', 'pass'),
        'postgresql://user:pass@db:5432/dbname',
    ),
    (
        ('db', 5432, 'dbname', '', ''),
        'postgresql://db:5432/dbname',
    ),
    (
        ('db', 5432, 'dbname', 'user', ''),
        'postgresql://user@db:5432/dbname',
    ),
    (
        ('', 0, 'dbname', '', ''),
        'postgresql:///dbname',
    ),
)


@pytest.mark.parametrize('config, expected', CASES)
def test_connection_string_formatting(config, expected):
    assert DatabaseConfig(*config).connstr == expected
