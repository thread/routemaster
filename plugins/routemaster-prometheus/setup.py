"""Package setup."""

from pathlib import Path

from setuptools import setup, find_packages

import version

long_description = (Path(__file__).parent / 'README.md').read_text()

setup(
    name='routemaster_prometheus',
    version=version.get_version(),
    url='https://github.com/thread/routemaster',
    description="Prometheus metrics reporting for Routemaster.",
    long_description=long_description,
    long_description_content_type="text/markdown",

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
        'prometheus_client>=0.4.2',
        'werkzeug>=2,<2.1',
    ),
)
