
routemaster-sentry
^^^^^^^^^^^^^^^^^^

Usage, in your Routemaster configuration file:

.. code-block:: yaml

   plugins:
     logging:
       - class: routemaster_sentry.logger:SentryLogger
         kwargs:
           dsn: https://xxxxxxx:xxxxxxx@sentry.io/xxxxxxx
