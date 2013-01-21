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

"""Module implementing the oxitopview bottle sub-window."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
from datetime import datetime

from PyQt4 import QtCore, QtGui

# Optional imports for file-export functionality
try:
    import oxitopdump.export_csv
    csv = True
except ImportError:
    csv = False
try:
    import oxitopdump.export_xls
    xls = True
except ImportError:
    xls = False


class BaseExporter(object):
    "Abstract base class for file export functionality"

    def __init__(self, parent):
        self.parent = parent
        self.title = ''

    def export_file(self):
        "Prompt the user for an export file-name to determine export format"
        exports = {}
        if csv:
            exports['.csv'] = (
                self.parent.tr('CSV - Comma separated values files'), self.export_csv)
        if xls:
            exports['.xls'] = (
                self.parent.tr('XLS - Excel files'), self.export_excel)
        if not exports:
            raise RuntimeError('Failed to load any export modules')
        filter_map = dict(
            ('%s (*%s)' % (name, ext), (ext, method))
            for (ext, (name, method)) in exports.items()
            )
        filter_string = ';;'.join(
            [self.parent.tr('All formats (%s)') % ' '.join('*' + ext for ext in exports)] +
            sorted(filter_map.keys())
            )
        (filename, filter_) = QtGui.QFileDialog.getSaveFileNameAndFilter(
            self.parent, self.title, os.getcwd(), filter_string)
        if filename:
            filename = str(filename)
            filter_ = str(filter_)
            os.chdir(os.path.dirname(filename))
            ext = os.path.splitext(filename)[1]
            if ext:
                # If the user has explicitly specified an extension then lookup
                # the method associated with the extension (if any)
                try:
                    export_method = exports[ext.lower()][1]
                except KeyError:
                    QtGui.QMessageBox.warning(
                        self, self.parent.tr('Warning'),
                        self.parent.tr('Unknown file extension "%s"') % ext)
                    return
            else:
                # Otherwise, use the filter label map we built earlier to
                # lookup the selected filter string and retrieve the default
                # extension which we append to the filename
                ext, export_method = filter_map[filter_]
                filename = filename + ext
            export_method(filename)

    def export_csv(self, filename):
        raise NotImplementedError

    def export_excel(self, filename):
        raise NotImplementedError

