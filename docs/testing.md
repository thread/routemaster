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

Routemaster requires Postgres and a database called `routemaster` for testing.

For now there is no way to migrate automatically, so the following SQL should
be run to set up the schema.

```sql
CREATE TABLE labels (
  name VARCHAR NOT NULL,
  state_machine VARCHAR NOT NULL,
  context JSONB,
  PRIMARY KEY (name, state_machine)
);

CREATE TABLE label_history (
  id SERIAL NOT NULL,
  label_name VARCHAR,
  label_state_machine VARCHAR,
  created TIMESTAMP WITHOUT TIME ZONE,
  forced BOOLEAN,
  old_state VARCHAR,
  new_state VARCHAR,
  PRIMARY KEY (id),
  FOREIGN KEY(label_name, label_state_machine) REFERENCES labels (name, state_machine)
);

CREATE TABLE state_machines (
  name VARCHAR NOT NULL,
  updated TIMESTAMP WITHOUT TIME ZONE,
  PRIMARY KEY (name)
);

CREATE TABLE states (
  name VARCHAR NOT NULL,
  state_machine INTEGER NOT NULL,
  deprecated BOOLEAN,
  updated TIMESTAMP WITHOUT TIME ZONE,
  PRIMARY KEY (name, state_machine),
  FOREIGN KEY(state_machine) REFERENCES state_machines (name)
);
```
