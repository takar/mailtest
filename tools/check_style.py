#!/usr/bin/env python
"""
Check the code style with flake8
"""

from __future__ import print_function
import os
import os.path
import subprocess
import sys


def main():
    """ The main function """
    directories_to_check = [
        'mailtest',
    ]

    script_directory = os.path.dirname(os.path.realpath(__file__))

    if os.name == 'nt':
        flake8 = os.path.join(sys.prefix, 'Scripts', 'flake8.exe')
    else:
        flake8 = os.path.join('flake8')

    rc = 0
    for d in directories_to_check:
        rc += subprocess.call([
            flake8,
            os.path.join(script_directory, '..', d)
        ])

    if rc == 0:
        sys.exit(0)
    else:
        print("Style check failed, please fix your code before committing.")
        sys.exit(1)


if __name__ == '__main__':
    """ Execute the main function"""
    main()
