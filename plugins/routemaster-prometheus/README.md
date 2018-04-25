### routemaster-prometheus

Usage, in your Routemaster configuration file:

```yaml
plugins:
  logging:
    - class: routemaster_prometheus.logger:PrometheusLogger
      kwargs:
        path: /metrics
```
