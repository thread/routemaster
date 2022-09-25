"""Package setup."""

from pathlib import Path

from setuptools import setup, find_packages

import version

long_description = (Path(__file__).parent / 'README.md').read_text()

setup(
    name='routemaster',
    version=version.get_version(),
    url='https://github.com/thread/routemaster',
    description="State machines as a service.",
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Office/Business',
    ),

    install_requires=(
        'click',
        'layer-loader',
        'pyyaml >= 5',
        'jsonschema >=3, <5',
        'flask',
        'psycopg2-binary',
        'sqlalchemy[mypy]',
        'python-dateutil',
        'alembic >=0.9.6',
        'gunicorn >=19.7',
        'werkzeug>=2,<2.1',
        'schedule',
        'freezegun',
        'requests',
        'networkx',
        'dataclasses',
        'typing-extensions>=3.7.4',
    ),

    setup_requires=(
        'pytest-runner',
    ),

    tests_require=(
        'pytest',
        'networkx',
        'tox',
        'pytest-cov',
        'pytest-pythonpath',
    ),

    entry_points={
        'console_scripts': (
            'routemaster = routemaster.cli:main',
        ),
    },
)
