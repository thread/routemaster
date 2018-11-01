"""Package setup."""

import version
from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

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
        'Topic :: Office/Business',
    ),

    install_requires=(
        'click',
        'pyyaml',
        'jsonschema >=2.6',
        'flask',
        'psycopg2',
        'sqlalchemy',
        'python-dateutil',
        'alembic >=0.9.6',
        'gunicorn >=19.7',
        'schedule',
        'freezegun',
        'requests',
        'networkx',
        'dataclasses',
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
