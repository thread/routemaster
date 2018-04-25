"""
Versioning utils.
"""

__all__ = ('get_version')

import os
import re
import logging
import os.path
import subprocess
from os.path import dirname

import pkg_resources

version_re = re.compile('^Version: (.+)$', re.M)

logger = logging.getLogger(__file__)


def find_git_root(test):
    prev, test = None, os.path.abspath(test)
    while prev != test:
        if os.path.isdir(os.path.join(test, '.git')):
            return test
        prev, test = test, os.path.abspath(os.path.join(test, os.pardir))
    return None


def get_version():
    """
    Gets the current version number.

    If in a git repository, it is the current git tag.
    Otherwise it is the one contained in the PKG-INFO file.
    To use this script, simply import it in your setup.py file
    and use the results of get_version() as your package version:
        from version import *
        setup(
            ...
            version=get_version(),
            ...
        )
    """
    git_root = find_git_root(dirname(__file__))

    if git_root is not None:
        # Get the version using "git describe".
        cmd = 'git describe --tags --match [0-9]*'.split()
        try:
            version = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            logger.exception('Unable to get version number from git tags')
            exit(1)

        # PEP 386 compatibility
        if '-' in version:
            version = '.post'.join(version.split('-')[:2])

        # Don't declare a version "dirty" merely because a time stamp has
        # changed. If it is dirty, append a ".dev1" suffix to indicate a
        # development revision after the release.
        with open(os.devnull, 'w') as fd_devnull:
            subprocess.call(
                ['git', 'status'],
                stdout=fd_devnull,
                stderr=fd_devnull,
            )

        cmd = 'git diff-index --name-only HEAD'.split()
        try:
            dirty = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            logger.exception('Unable to get git index status')
            exit(1)

        if dirty != '':
            version += '.dev1'

        return version

    else:
        try:
            return pkg_resources.working_set.by_key[
                'routemaster_prometheus'
            ].version
        except KeyError:
            return '0.0.0-unreleased'
