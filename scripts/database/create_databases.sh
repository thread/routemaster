#!/bin/bash -ex

# Create the development database
createdb -E utf-8 routemaster

# Create the test database
createdb -E utf-8 routemaster_test

# Run the migrations for the development database
alembic upgrade head
