# Migrations setup

Routemaster uses [`alembic`][alembic] for its migrations, and supports
Postgres for its data storage.

## I need to set up my database up for the first time

1. Create a database for Routemaster to use.
2. Set up access credentials for the database in your Routemaster config.
3. Edit `alembic.ini` to point at the config file you are using.
4. Run `alembic upgrade head`

Note: if you already have a local PostgreSQL database server configured, then
you may be able to just run the `scripts/database/create_databases.sh` script.

## I need to apply migrations to bring myself up to date

The equivalent of the Django: `manage.py migrate`

Is: `alembic upgrade head`

## I have edited the models and need to create a migration

1. Run `alembic revision --autogenerate -m "<message>"`
2. Edit the file it just created, to sanity check and tidy it up
3. `alembic upgrade head` to apply it.

Note a few differences from `setup.py makemigrations`:

* The revision message is not an optional feature,
* Alembic migrations look a lot messier than Django migrations,
* Due to the (much!) greater flexibility SQLAlchemy has compared with the
  Django ORM, migration systems have a much harder time reliably detecting
  changes and generating DDL. This means you _always_ need to check and revise
  what Alembic generates in its migrations.
* The revision IDs are _not_, in general, date-ordered or sequential: the IDs
  are random and the sequencing is declared programmatically in the migrations.
  You can get the "sensible" history with `alembic history`.


[alembic]: http://alembic.zzzcomputing.com/en/latest/
