"""Package setup."""

import version
from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

try:
    from m2r import convert
    long_description = convert(long_description)
except ImportError:
    # Fall back to markdown formatted readme when no m2r package.
    pass


setup(
    name='routemaster_sentry',
    version=version.get_version(),
    url='https://github.com/thread/routemaster',
    description="Sentry error reporting for Routemaster.",
    long_description=long_description,

    author="Thread",
    author_email="tech@thread.com",

    keywords=(
    ),
    license='MIT',

    zip_safe=False,

    packages=find_packages(),
    include_package_data=True,

    classifiers=(
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Topic :: Office/Business',
    ),

    install_requires=(
        'routemaster',
        'raven[flask]',
    ),
)
