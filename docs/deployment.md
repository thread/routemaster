# Deployment

### Docker

Deploying with Docker is the recommended deployment strategy.

Either create your own Dockerfile that inherits from `routemaster` and replaces `/routemaster/config/config.yaml` with your configuration, or deploy the `routemaster` image directly, mounting your own config in place.

You will need to expose the database to the running container, and provide connection settings either through the config file or through environment variables: `DB_{HOST,PORT,NAME,USER,PASS}`. Note that the environment variables will override the config file.
