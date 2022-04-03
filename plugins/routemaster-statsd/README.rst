
routemaster-statsd
^^^^^^^^^^^^^^^^^^

Usage, in your Routemaster configuration file:

.. code-block:: yaml

   plugins:
     logging:
       - class: routemaster_statsd.logger:StatsDLogger
         kwargs:
           host: localhost
           port: 8800
           tags:
             environment: production

This plugin will send metrics over UDP to a compatible StatsD server.

The host and port can also be specified through environment variable
(``STATSD_HOST`` and ``STATSD_PORT``). The default is ``localhost:8125``.

The statsd tags will be send in `Dogstatsd
<https://docs.datadoghq.com/developers/dogstatsd/datagram_shell/>`_'s format
which is widely supported.
