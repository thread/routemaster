# Releasing Routemaster Versions

Releases are handled by CircleCI. To perform a release:

1. Push the commit to master that you wish to release.
2. Wait for the build to complete successfully.
3. Tag the commit appropriately, and `git push --tags`.
4. Wait for CircleCI to rebuild, and then release.


### Versions

The tag for a release must be the version number to be published.

We roughly follow semantic versioning. The public API should be considered to
be the information provided by the web API, the file format for configuration,
and the _logical_ behaviour of the state machine.

Note that state machine behaviour changes such as optimisations, or fixes to
be more correct, should not be considered breaking changes.


### What's in a release?

A release consists of:

 - A `routemaster` package uploaded, with the specified version number, to
   PyPI.
 - A package for each plugin in the `plugins` directory, with the _same
   version number_, uploaded to PyPI.
 - A Docker image built with all of the above installed in it, and pushed to
   `thread/routemaster` on Docker Hub.
