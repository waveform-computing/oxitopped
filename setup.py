#!/usr/bin/env python
# vim: set et sw=4 sts=4:

# Copyright 2012 Dave Hughes.
#
# This file is part of oxitopped.
#
# oxitopped is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# oxitopped is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# oxitopped.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (
    # XXX Alright! I give in! Distutils and all its myriad extensions (py2exe,
    # py2app, et al.) are all too shit to handle unicode with barfing all over
    # the floor, so out goes the following line...
    #unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
from setuptools import setup, find_packages
from utils import description, get_version, require_python

HERE = os.path.abspath(os.path.dirname(__file__))

# Workaround <http://bugs.python.org/issue10945>
import codecs
try:
    codecs.lookup('mbcs')
except LookupError:
    ascii = codecs.lookup('ascii')
    func = lambda name, enc=ascii: {True: enc}.get(name=='mbcs')
    codecs.register(func)

require_python(0x020600f0)

# All meta-data is defined as global variables so that other modules can query
# it easily without having to wade through distutils nonsense
NAME         = 'oxitopped'
DESCRIPTION  = 'Tools for extracting data from an OxiTop OC110 data logger'
KEYWORDS     = ['science', 'gas', 'bottle', 'oxitop']
AUTHOR       = 'Dave Hughes'
AUTHOR_EMAIL = 'dave@waveform.org.uk'
MANUFACTURER = 'waveform'
URL          = 'https://www.waveform.org.uk/oxitopped/'

REQUIRES = [
    'pyserial',
    'distribute',
    ]

EXTRA_REQUIRES = {
    'XLS':        ['xlwt'],
    'GUI':        ['pyqt', 'matplotlib', 'numpy'],
    'daemon':     ['python-daemon'],
    'completion': ['optcomplete'],
    }

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Environment :: Win32 (MS Windows)',
    'Environment :: X11 Applications :: Qt',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Operating System :: Unix',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Scientific/Engineering',
    ]

ENTRY_POINTS = {
    'console_scripts': [
        'oxitoplist = oxitopped.oxitoplist:main',
        'oxitopdump = oxitopped.oxitopdump:main',
        'oxitopemu = oxitopped.oxitopemu:main',
        ],
    'gui_scripts': [
        'oxitopview = oxitopped.oxitopview:main',
        ],
    }

PACKAGES = [
    'oxitopped',
    'oxitopped.windows',
    ]

PACKAGE_DATA = {
    'oxitopped': [
        '*.xml',
        ],
    'oxitopped.windows': [
        '*.ui',
        os.path.join('fallback-theme', '*.png'),
        os.path.join('fallback-theme', '*.svg'),
        ],
    }


def main():
    setup(
        name                 = NAME,
        version              = get_version(os.path.join(HERE, NAME, '__init__.py')),
        description          = DESCRIPTION,
        long_description     = description(os.path.join(HERE, 'README.rst')),
        classifiers          = CLASSIFIERS,
        author               = AUTHOR,
        author_email         = AUTHOR_EMAIL,
        url                  = URL,
        keywords             = ' '.join(KEYWORDS),
        packages             = PACKAGES,
        package_data         = PACKAGE_DATA,
        platforms            = 'ALL',
        install_requires     = REQUIRES,
        extras_require       = EXTRA_REQUIRES,
        zip_safe             = True,
        test_suite           = NAME,
        entry_points         = ENTRY_POINTS,
        )

if __name__ == '__main__':
    main()
