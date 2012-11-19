#!/usr/bin/env python
# vim: set et sw=4 sts=4:

# Copyright 2012 Dave Hughes.
#
# This file is part of oxitopdump.
#
# oxitopdump is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# oxitopdump is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# oxitopdump.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

from setuptools import setup, find_packages
from utils import description, get_version, require_python

# Workaround <http://bugs.python.org/issue10945>
import codecs
try:
    codecs.lookup('mbcs')
except LookupError:
    ascii = codecs.lookup('ascii')
    func = lambda name, enc=ascii: {True: enc}.get(name=='mbcs')
    codecs.register(func)

require_python(0x020600f0)

classifiers = [
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Operating System :: Unix',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Scientific/Engineering',
]

entry_points = {
    'console_scripts': [
        'oxitopdump = oxitopdump:main',
    ]
}


def main():
    setup(
        name                 = 'oxitopdump',
        version              = get_version('oxitopdump/__init__.py'),
        description          = 'A tool for extracting data from an OxiTop data logger',
        long_description     = description('README.rst'),
        author               = 'Dave Hughes',
        author_email         = 'dave@waveform.org.uk',
        url                  = '',
        packages             = find_packages(exclude=['distribute_setup', 'utils']),
        install_requires     = ['pyserial'],
        extras_require       = {},
        include_package_data = True,
        platforms            = 'ALL',
        zip_safe             = False,
        entry_points         = entry_points,
        classifiers          = classifiers
    )

if __name__ == '__main__':
    main()
