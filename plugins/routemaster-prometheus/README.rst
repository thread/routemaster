
routemaster-prometheus
^^^^^^^^^^^^^^^^^^^^^^

Usage, in your Routemaster configuration file:

.. code-block:: yaml

   plugins:
     logging:
       - class: routemaster_prometheus.logger:PrometheusLogger
         kwargs:
           path: /metrics

This package is based on the official Python Promeutheus bindings in
`\ ``prometheus_client`` <https://pypi.org/project/prometheus_client/>`_. In order
for that package to operate in a multithreaded program such as Routemaster,
the environment variable ``prometheus_multiproc_dir`` must be set to a writeable
directory for temporary files. It does not need to be backed up as nothing
is persisted between application launches.

This is already done for you in the ``thread/routemaster`` Docker image
provided, but when deploying in a custom way you may wish to change this
directory.
