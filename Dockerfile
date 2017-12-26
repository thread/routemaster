FROM python:3.6-stretch

ENV PYTHONUNBUFFERED 1

WORKDIR /routemaster/app

COPY . .
RUN pip install --no-cache-dir .

WORKDIR /routemaster/config
COPY scripts/build/default_config.yaml config.yaml

EXPOSE 2017

ENTRYPOINT ["routemaster"]
CMD ["serve", "--config-file=config.yaml"]
