# Testing setup

### Tox

Routemaster requires `tox` to run the tests. See the README for the basic info
on how to run tests.

##### Running after changed dependencies

`tox` uses virtualenvs to contain the tests. These are not created every time
the tests are run, which means we have to reset them manually if the
requirements (or `setup.py` "install requires") change.

Just `rm -rf .tox/py36` to reset the main testing virtualenv, or replace `py36`
with `lint` or `mypy` to do the same for those environments.


### Database

Routemaster requires Postgres and a database called `routemaster_test` for
testing.
