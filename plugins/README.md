# Plugins

Routemaster currently supports plugins for logging purposes.

These "logging" plugins are not strictly about _logging_, but include error
reporting and metrics of the behaviour of Routemaster.

In scope (and accepted plugin pull-requests) would include:

 - Error reporters for tools like Rollbar.
 - Metrics reporters for tools like Prometheus or Data Dog.
 - Logging reporters for tools like Papertrail.

The plugin API defined in `routemaster.logging.BaseLogger` is relatively basic
so far, and any changes that extend the functionality of it to better support
the above plugin use-cases would be welcomed.
