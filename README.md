# Routemaster

[![CircleCI](https://circleci.com/gh/thread/routemaster.svg?style=shield&circle-token=3973777302b4f7f00f5b9eb1c07e3c681ea94f35)](https://circleci.com/gh/thread/routemaster)

State machines as a service.

(The _master_ of _routes_ through a state machine.)

Routemaster targets Python 3.6 and above.

### Development setup

You'll need to create a database for developing against and for running tests
against. This can be done by running the `./create_databases.sh` script.

### Testing, Linting and Typechecking

Testing and linting are done by `tox`, which manages its own virtual
environments for you.

The following should be sufficient to run a full test and lint process as done
by the CI.

```shell
$ pip install tox
$ tox
```

To run the tests outside of `tox` (i.e. to be able to pass complex parameters
to pytest):

```shell
$ pip install -r scripts/testing/requirements.txt
$ py.test
```

To run the linting outside of `tox` (i.e. possibly for integration with an
editor):

```shell
$ pip install -r scripts/linting/requirements.txt
$ flake8 routemaster
```

To run the type checking outside of `tox` (again possibly for editor
integration):

```shell
$ pip install -r scripts/linting/requirements.txt
$ mypy -p routemaster
```
