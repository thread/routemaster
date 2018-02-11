"""
Versioning utils.
"""

__all__ = ('get_version')

import os
import re
import logging
import subprocess
from os.path import join, isdir, dirname

version_re = re.compile('^Version: (.+)$', re.M)

logger = logging.getLogger(__file__)


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
    d = join(dirname(dirname(__file__)))

    if isdir(join(d, '.git')):
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
            subprocess.call(['git', 'status'],
                            stdout=fd_devnull, stderr=fd_devnull)

        cmd = 'git diff-index --name-only HEAD'.split()
        try:
            dirty = subprocess.check_output(cmd).decode().strip()
        except subprocess.CalledProcessError:
            logger.exception('Unable to get git index status')
            exit(1)

        if dirty != '':
            version += '.dev1'

    else:
        # Extract the version from the PKG-INFO file.
        with open(join(d, 'PKG-INFO')) as f:
            version = version_re.search(f.read()).group(1)

    return version
