# -*- coding: utf-8 -*-
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

"""Main module for the oxitopview application."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import sys
import logging

import sip
for api in ('QDate', 'QDateTime', 'QTime', 'QString', 'QTextStream', 'QUrl', 'QVariant'):
    sip.setapi(api, 2)
from PyQt4 import QtCore, QtGui

from oxitopdump import __version__
from oxitopdump.oxitopview.main_window import MainWindow


APPLICATION = None
MAIN_WINDOW = None

def excepthook(type, value, tb):
    # XXX Need to expand this to display a complete stack trace and add an
    # e-mail option for bug reports
    QtGui.QMessageBox.critical(
        QtGui.QApplication.instance().activeWindow(),
        QtGui.QApplication.instance().desktop().tr('Error'),
        str(value))

def main(args=None):
    global APPLICATION, MAIN_WINDOW
    if args is None:
        args = sys.argv
    if ('-D' in args) or ('--debug' in args):
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter('%(message)s'))
        console.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(console)
        logging.getLogger().setLevel(logging.DEBUG)
    APPLICATION = QtGui.QApplication(args)
    APPLICATION.setApplicationName('oxitopview')
    APPLICATION.setApplicationVersion(__version__)
    APPLICATION.setOrganizationName('Waveform')
    APPLICATION.setOrganizationDomain('waveform.org.uk')
    MAIN_WINDOW = MainWindow()
    MAIN_WINDOW.show()
    return APPLICATION.exec_()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
