FROM python:3.6-stretch

ENV PYTHONUNBUFFERED 1

WORKDIR /routemaster/app

COPY routemaster/migrations/ routemaster/migrations/

COPY dist/ .

# Install first-party plugins (inactive by default).
COPY plugins/routemaster-sentry/dist/ .
COPY plugins/routemaster-prometheus/dist/ .

RUN pip install --no-cache-dir *.whl

COPY scripts/build/default_config.yaml config.yaml
COPY alembic.ini alembic.ini

EXPOSE 2017

ENV prometheus_multiproc_dir /tmp/routemaster/prometheus

CMD ["routemaster", "--config-file=config.yaml", "serve"]
