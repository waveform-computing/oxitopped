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

"""Module implementing the CSV export dialog."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import csv
from datetime import datetime

from PyQt4 import QtCore, QtGui, uic

from oxitopped.windows import get_ui_file


DEFAULT_DELIMITER = ','
DEFAULT_LINETERMINATOR = '\r\n'
DEFAULT_QUOTECHAR = '"'
DEFAULT_QUOTING = csv.QUOTE_MINIMAL
DEFAULT_HEADER_ROW = False
DEFAULT_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


class ExportCsvDialog(QtGui.QDialog):
    "Implements the file/export dialog for CSV files"

    column_separators = [b',', b';', b' ', b'\t']
    line_terminators = [b'\r\n', b'\n', b'\r']
    quote_marks = [b'"', b"'"]
    quote_behaviours = [
        csv.QUOTE_ALL,
        csv.QUOTE_NONNUMERIC,
        csv.QUOTE_MINIMAL,
        csv.QUOTE_NONE,
        ]

    def __init__(self, parent=None):
        super(ExportCsvDialog, self).__init__(parent)
        self.ui = uic.loadUi(get_ui_file('export_csv_dialog.ui'), self)
        # Read the last-used lists
        self.settings = self.parent().window().settings
        self.settings.beginGroup('export_csv')
        try:
            self.delimiter = self.settings.value('delimiter', DEFAULT_DELIMITER)
            self.lineterminator = self.settings.value('lineterminator', DEFAULT_LINETERMINATOR)
            self.quotechar = self.settings.value('quotechar', DEFAULT_QUOTECHAR)
            self.quoting = int(self.settings.value('quoting', DEFAULT_QUOTING))
            self.header_row = bool(self.settings.value('header_row', DEFAULT_HEADER_ROW))
            self.timestamp_format = self.settings.value('timestamp_format', DEFAULT_TIMESTAMP_FORMAT)
        finally:
            self.settings.endGroup()
        # Connect up signals
        self.ui.timestamp_default_button.clicked.connect(self.timestamp_default_clicked)
        self.ui.timestamp_format_edit.textChanged.connect(self.timestamp_format_changed)
        self.timestamp_format_changed()

    def accept(self):
        "Called when the user closes the dialog successfully"
        super(ExportCsvDialog, self).accept()
        self.settings.beginGroup('export_csv')
        try:
            self.settings.setValue('delimiter', self.delimiter)
            self.settings.setValue('lineterminator', self.lineterminator)
            self.settings.setValue('quotechar', self.quotechar)
            self.settings.setValue('quoting', self.quoting)
            self.settings.setValue('header_row', self.header_row)
            self.settings.setValue('timestamp_format', self.timestamp_format)
        finally:
            self.settings.endGroup()

    def _get_delimiter(self):
        return self.column_separators[
            self.ui.column_separator_combo.currentIndex()]

    def _set_delimiter(self, value):
        self.ui.column_separator_combo.setCurrentIndex(
            self.column_separators.index(value))

    def _get_lineterminator(self):
        return self.line_terminators[
            self.ui.line_terminator_combo.currentIndex()]

    def _set_lineterminator(self, value):
        self.ui.line_terminator_combo.setCurrentIndex(
            self.line_terminators.index(value))

    def _get_quotechar(self):
        return self.quote_marks[
            self.ui.quote_marks_combo.currentIndex()]

    def _set_quotechar(self, value):
        self.ui.quote_marks_combo.setCurrentIndex(
            self.quote_marks.index(value))

    def _get_quoting(self):
        return self.quote_behaviours[
            self.ui.quote_behaviour_combo.currentIndex()]

    def _set_quoting(self, value):
        self.ui.quote_behaviour_combo.setCurrentIndex(
            self.quote_behaviours.index(value))

    def _get_header_row(self):
        return self.ui.header_check.isChecked()

    def _set_header_row(self, value):
        self.ui.header_check.setChecked(bool(value))

    def _get_timestamp_format(self):
        return self.ui.timestamp_format_edit.text()

    def _set_timestamp_format(self, value):
        self.ui.timestamp_format_edit.setText(value)

    delimiter = property(_get_delimiter, _set_delimiter)
    lineterminator = property(_get_lineterminator, _set_lineterminator)
    quotechar = property(_get_quotechar, _set_quotechar)
    quoting = property(_get_quoting, _set_quoting)
    header_row = property(_get_header_row, _set_header_row)
    timestamp_format = property(_get_timestamp_format, _set_timestamp_format)

    def timestamp_format_changed(self, value=None):
        "Called to update the dialog buttons when timestamp_format_edit changes"
        try:
            self.ui.timestamp_example_label.setText(datetime.now().strftime(
                self.ui.timestamp_format_edit.text()))
            self.ui.timestamp_example_label.setPalette(QtGui.QPalette())
            valid = True
        except ValueError as exc:
            self.ui.timestamp_example_label.setText(str(exc))
            warning_palette = QtGui.QPalette()
            warning_palette.setColor(QtGui.QPalette.WindowText,
                QtGui.QColor(255, 0, 0))
            self.ui.timestamp_example_label.setPalette(warning_palette)
            valid = False
        self.ui.button_box.button(QtGui.QDialogButtonBox.Ok).setEnabled(valid)

    def timestamp_default_clicked(self):
        "Event handler for the timestamp Default button"
        self.ui.timestamp_format_edit.setText(DEFAULT_TIMESTAMP_FORMAT)

