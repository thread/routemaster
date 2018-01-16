# Getting Started

## Development Setup

You'll need to create a database for developing against and for running tests
against. This can be done by running the `scripts/database/create_databases.sh`
script. Full details of how the database, models & migrations are handled can be
found in the [migrations docs](docs/migrations.md). Routemaster requires
Postgres.

#### Tox

Testing, linting and type checking are done by `tox`, which manages its own virtual
environments for you.

The following should be sufficient to run a full test and lint process as done
by the CI.

```shell
$ pip install tox
$ tox
```

#### Testing

To run the tests outside of `tox` (i.e. to be able to pass complex parameters
to pytest):

```shell
$ pip install -r scripts/testing/requirements.txt
$ py.test
```

#### Linting

To run the linting outside of `tox` (i.e. possibly for integration with an
editor):

```shell
$ pip install -r scripts/linting/requirements.txt
$ flake8 routemaster
```

#### Type checking

To run the type checking outside of `tox` (again possibly for editor
integration):

```shell
$ pip install -r scripts/linting/requirements.txt
$ mypy -p routemaster
```


##### Running after changed dependencies

`tox` uses virtualenvs to contain the tests. These are not created every time
the tests are run, which means we have to reset them manually if the
requirements (or `setup.py` "install requires") change.

Run tox with the "recreate" flag to force a reinstall of the dependencies.

```shell
$ tox --recreate
```
