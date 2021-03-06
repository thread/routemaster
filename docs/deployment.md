# Deployment

### Docker

Deploying with Docker is the recommended deployment strategy.

Either create your own Dockerfile that inherits from
[`thread/routemaster`](https://hub.docker.com/r/thread/routemaster/) and
replaces the file `/routemaster/config/config.yaml` with your configuration, or
deploy the `routemaster` image directly, mounting your own config in place.

You will need to expose the database to the running container, and provide
connection through environment variables: `DB_HOST`, `DB_PORT`, `DB_NAME`,
`DB_USER`, `DB_PASS`.


##### Migrations

Migrations are not run automatically by the Docker container. It is recommended
that you include a migration process in your deployment. A basic version of
this is:

```shell
docker stop routemaster
docker run --rm thread/routemaster alembic upgrade head
docker start routemaster
```


### Python

Routemaster and its plugins are packaged as Python packages and deployed to
PyPI. You can install and run Routemaster on any machine with Python 3.6 by
using `pip`.
