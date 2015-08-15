#!/usr/bin/env python

from distutils.core import setup

setup(name='mailtest',
    version='0.1',
    description='Check sending and receiving mails',
    author='Tamar Kranenburg',
    author_email='info@takar.nl',
    url='https://github.com/takar/mailtest',
    scripts=['mailtest/mailtest.py']
)
