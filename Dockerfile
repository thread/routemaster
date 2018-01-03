FROM python:3.6-stretch

ENV PYTHONUNBUFFERED 1

WORKDIR /routemaster/app

COPY . .
RUN pip install --no-cache-dir .

COPY scripts/build/default_config.yaml config.yaml
COPY alembic.ini alembic.ini

EXPOSE 2017

CMD ["routemaster", "--config-file=config.yaml", "serve"]
