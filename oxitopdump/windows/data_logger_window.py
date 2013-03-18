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

"""Module implementing the oxitopview data logger sub-window."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import io
import os
from datetime import datetime

from PyQt4 import QtCore, QtGui, uic

from oxitopdump.oxitopview.bottle_window import BottleWindow
from oxitopdump.oxitopview.exporter import BaseExporter
from oxitopdump.oxitopview.export_csv_dialog import ExportCsvDialog
from oxitopdump.oxitopview.export_excel_dialog import ExportExcelDialog

# XXX Py3
try:
    basestring
except NameError:
    basestring = str


MODULE_DIR = os.path.abspath(os.path.dirname(__file__))


class DataLoggerWindow(QtGui.QWidget):
    "Document window for the data logger connection"

    def __init__(self, data_logger):
        super(DataLoggerWindow, self).__init__(None)
        self.ui = uic.loadUi(
            os.path.join(MODULE_DIR, 'data_logger_window.ui'), self)
        self.ui.bottles_view.setModel(DataLoggerModel(data_logger))
        for col in range(self.ui.bottles_view.model().columnCount()):
            self.ui.bottles_view.resizeColumnToContents(col)
        self.ui.bottles_view.doubleClicked.connect(
            self.bottles_view_double_clicked)
        # TODO What about pressing Enter instead of double clicking?
        self.setWindowTitle(
            '%s on %s' % (data_logger.id, data_logger.port.port))
        self.exporter = DataLoggerExporter(self)

    def closeEvent(self, event):
        "Called when the window is closed"
        self.data_logger.close()
        event.accept()

    @property
    def data_logger(self):
        return self.ui.bottles_view.model().data_logger

    def bottles_view_double_clicked(self, index):
        "Handler for the bottles_view double-click event"
        bottle = self.data_logger.bottles[index.row()]
        for window in self.window().ui.mdi_area.subWindowList():
            if isinstance(window.widget(), BottleWindow) and (
                    window.widget().bottle == bottle):
                self.window().ui.mdi_area.setActiveSubWindow(window)
                return
        window = None
        try:
            window = self.window().ui.mdi_area.addSubWindow(
                BottleWindow(bottle))
            window.show()
        except KeyboardInterrupt:
            if window is not None:
                window.close()

    def export_file(self):
        "Export the bottle list to a user-specified filename"
        self.exporter.export_file()

    def refresh_window(self):
        "Forces the list to be re-read from the data logger"
        model = self.ui.bottles_view.model()
        first = model.index(0, 0)
        last = model.index(model.rowCount() - 1, model.columnCount() - 1)
        model.data_logger.refresh()
        # Have the model inform the view that all items (from first to last)
        # have changed
        model.dataChanged.emit(first, last)


class DataLoggerModel(QtCore.QAbstractTableModel):
    def __init__(self, data_logger):
        super(DataLoggerModel, self).__init__()
        self.data_logger = data_logger

    def rowCount(self, parent=None):
        if parent is None:
            parent = QtCore.QModelIndex()
        if parent.isValid():
            return 0
        return len(self.data_logger.bottles)

    def columnCount(self, parent=None):
        if parent is None:
            parent = QtCore.QModelIndex()
        if parent.isValid():
            return 0
        return 9

    def data(self, index, role):
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole:
            return None
        bottle = self.data_logger.bottles[index.row()]
        return [
            bottle.serial,
            bottle.id,
            bottle.start.strftime('%c'),
            bottle.finish.strftime('%c'),
            bottle.mode_string,
            '%.1fml' % bottle.bottle_volume,
            '%.1fml' % bottle.sample_volume,
            '1+%d' % bottle.dilution,
            str(len(bottle.heads)),
            ][index.column()]

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return [
                'Bottle Serial',
                'ID',
                'Start',
                'Finish',
                'Mode',
                'Bottle Vol',
                'Sample Vol',
                'Dilution',
                'Heads',
                ][section]
        elif orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return section + 1


class DataLoggerExporter(BaseExporter):
    "Data exporter class for the data logger"

    def __init__(self, parent):
        super(DataLoggerExporter, self).__init__(parent)
        self.title = self.parent.tr('Export bottles list')

    def export_csv(self, filename):
        "Export the bottle list to a CSV file"
        dialog = ExportCsvDialog(self.parent)
        if dialog.exec_():
            from oxitopdump.export_csv import CsvExporter
            exporter = CsvExporter()
            exporter.delimiter = dialog.delimiter
            exporter.lineterminator = dialog.lineterminator
            exporter.quotechar = dialog.quotechar
            exporter.quoting = dialog.quoting
            exporter.header_row = dialog.header_row
            exporter.timestamp_format = dialog.timestamp_format
            exporter.export_bottles(filename, self.parent.data_logger.bottles)

    def export_excel(self, filename):
        "Export the bottle list to an Excel file"
        dialog = ExportExcelDialog(self.parent)
        if dialog.exec_():
            from oxitopdump.export_xls import ExcelExporter
            exporter = ExcelExporter()
            exporter.header_row = dialog.header_row
            exporter.row_colors = dialog.row_colors
            exporter.export_bottles(filename, self.parent.data_logger.bottles)

