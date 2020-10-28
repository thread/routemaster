
routemaster-statsd
^^^^^^^^^^^^^^^^^^

Usage, in your Routemaster configuration file:

.. code-block:: yaml

   plugins:
     logging:
       - class: routemaster_statsd.logger:StatsdLogger
         kwargs:
           tags:
            environment: production
            host: localhost
            port: 8800

- This plugin will send metrics over UDP.
- The host and port can also be specified through environment variable
(`STATSD_HOST` and `STATSD_PORT`). The default is `localhost:8125`.
- The statsd tags will be send in `Dogstatsd
<https://docs.datadoghq.com/developers/dogstatsd/datagram_shell/>`_'s format
which is widely supported.
