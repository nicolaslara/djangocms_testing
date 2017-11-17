#!/usr/bin/env python
from setuptools import find_packages, setup

long_description = open('README.md').read()

setup(
    name='djangocms_testing',
    version='0.1',
    description='Testing utilities for Django CMS',
    long_description=long_description,
    author='Nicolas Lara',
    author_email='nicolas@lincolnloop.com',
    url='https://github.com/nicolaslara/djangocms_testing/',
    packages=find_packages(),
    scripts=[
    ],
    package_data={
        'djangocms_testing': ['djangocms_testing/templates/*.*'],
    },
    include_package_data=True,
    install_requires=[
        'django-cms>=3.4.5',
        'PyYAML>=3.12',
    ],
)
