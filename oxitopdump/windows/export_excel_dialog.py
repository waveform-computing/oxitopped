# -*- coding: utf-8 -*-
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

"""Module implementing the Excel export dialog."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import xlwt

from PyQt4 import QtCore, QtGui, uic

from oxitopped.windows import get_ui_file


DEFAULT_HEADER_ROW = False
DEFAULT_ROW_COLORS = False


class ExportExcelDialog(QtGui.QDialog):
    "Implements the file/export dialog for CSV files"

    def __init__(self, parent=None):
        super(ExportExcelDialog, self).__init__(parent)
        self.ui = uic.loadUi(get_ui_file('export_excel_dialog.ui'), self)
        # Read the last-used lists
        self.settings = self.parent().window().settings
        self.settings.beginGroup('export_excel')
        try:
            self.header_row = bool(self.settings.value('header_row', DEFAULT_HEADER_ROW))
            self.row_colors = bool(self.settings.value('row_colors', DEFAULT_ROW_COLORS))
        finally:
            self.settings.endGroup()

    def accept(self):
        "Called when the user closes the dialog successfully"
        super(ExportExcelDialog, self).accept()
        self.settings.beginGroup('export_excel')
        try:
            self.settings.setValue('header_row', self.header_row)
            self.settings.setValue('row_colors', self.row_colors)
        finally:
            self.settings.endGroup()

    def _get_header_row(self):
        return self.ui.header_check.isChecked()

    def _set_header_row(self, value):
        self.ui.header_check.setChecked(bool(value))

    def _get_row_colors(self):
        return self.ui.row_colors_check.isChecked()

    def _set_row_colors(self, value):
        self.ui.row_colors_check.setChecked(bool(value))

    header_row = property(_get_header_row, _set_header_row)
    row_colors = property(_get_row_colors, _set_row_colors)

