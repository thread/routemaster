# Migrations setup

Routemaster uses [`alembic`][alembic] for its migrations, and supports
Postgres for its data storage.


### I need to set up my database up for the first time

1. Create a database for Routemaster to use.

   Note: if you already have a local PostgreSQL database server configured,
   then you may be able to just run the `scripts/database/create_databases.sh`
   script.

2. Set up access credentials for the database in your environment variables.

    You'll probably want to set `DB_USER` (defaults to `routemaster`) and
    `DB_PASS` for running, though you also need to set `PG_USER` and `PG_PASS`
    for the tests to use.

    A convenient way to do this is to add these to a `.env` file in the root of
    the repo and then source that file as part of `postactivate` in your
    virtualenv.

3. Run `alembic upgrade head`


### I need to apply migrations to bring myself up to date

Run `alembic upgrade head`. This is equivalent it `manage.py migrate` in
Django.


### I have edited the models and need to create a migration

1. Run `alembic revision --autogenerate -m "<message>"`
2. Edit the file it just created, to sanity check and tidy it up.
3. `alembic upgrade head` to apply it.

If you are familiar with Django migrations there are a few differences to
`makemigrations` to note:

* The revision message is not an optional feature
* Due to the greater flexibility SQLAlchemy has compared with the
  Django ORM, migration systems have a much harder time reliably detecting
  changes and generating DDL. This means you _always_ need to check and revise
  what Alembic generates in its migrations.
* The revision IDs are _not_, in general, date-ordered or sequential: the IDs
  are random and the sequencing is declared programmatically in the migrations.
  You can get the "sensible" history with `alembic history`.

[alembic]: http://alembic.zzzcomputing.com/en/latest/
