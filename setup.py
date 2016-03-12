"""
Flask-URS
=========

Flask-URS is a Flask extension that adds basic Json Web Token features to any application based
upon NASA EarthData Oauth2.

Resources
---------

* `Documentation <http://packages.python.org/Flask-URS/>`_
* `Issue Tracker <https://github.com/justinwp/flask-urs/issues>`_
* `Source <https://github.com/justinwp/flask-urs-jwt>`_
* `Development Version
  <https://github.com/justinwp/flask-urs-jwt/raw/develop#egg=Flask-URS-dev>`_

"""

import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


def get_requirements(suffix=''):
    with open('requirements%s.txt' % suffix) as f:
        rv = f.read().splitlines()
    return rv


def get_long_description():
    with open('README.rst') as f:
        rv = f.read()
    return rv


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = [
            '-xrs',
            '--cov', 'flask_urs',
            '--cov-report', 'term-missing',
            '--pep8',
            '--flakes',
            '--clearcache',
            'tests'
        ]
        self.test_suite = True

    def run_tests(self):
        import pytest

        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='Flask-URS',
    version='0.1.3',
    url='https://github.com/justinwp/flask-urs',
    download_url='https://github.com/justinwp/flask-urs/tarball/0.1.2',
    license='MIT',
    author='Justin Poehnelt',
    author_email='Justin.Poehnelt@gmail.com',
    description='JWT token authentication using NASA URS Oauth2 for Flask apps',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=get_requirements(),
    tests_require=get_requirements('-dev'),
    cmdclass={'test': PyTest},
    classifiers=[
        "Development Status :: 3 - Alpha",
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
