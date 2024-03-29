"""Package setup."""

from setuptools import setup, find_packages

import version

with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='routemaster_statsd',
    version=version.get_version(),
    url='https://github.com/thread/routemaster',
    description="Statsd metrics reporting for Routemaster.",
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
        'statsd_python',
        'werkzeug>=2,<2.1',
    ),
)
