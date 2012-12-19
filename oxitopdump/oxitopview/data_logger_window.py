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
            import csv
            with io.open(filename, 'wb') as output_file:
                writer = csv.writer(output_file,
                    delimiter=dialog.delimiter,
                    lineterminator=dialog.lineterminator,
                    quotechar=dialog.quotechar,
                    quoting=dialog.quoting,
                    doublequote=csv.excel.doublequote)
                if dialog.header_row:
                    writer.writerow((
                        'Serial',
                        'ID',
                        'Start',
                        'Finish',
                        'Mode',
                        'Bottle Vol',
                        'Sample Vol',
                        'Dilution',
                        'Heads',
                        ))
                for bottle in self.parent.data_logger.bottles:
                    row = (
                        bottle.serial,
                        bottle.id,
                        bottle.start.strftime(dialog.timestamp_format),
                        bottle.finish.strftime(dialog.timestamp_format),
                        bottle.mode_string,
                        bottle.bottle_volume,
                        bottle.sample_volume,
                        bottle.dilution,
                        len(bottle.heads),
                        )
                    writer.writerow(row)

    def export_excel(self, filename):
        "Export the bottle list to an Excel file"
        dialog = ExportExcelDialog(self.parent)
        if dialog.exec_():
            import xlwt
            header_style = xlwt.easyxf('font: bold on')
            even_default_style = xlwt.easyxf('')
            even_text_style = xlwt.easyxf(num_format_str='@')
            even_date_style = xlwt.easyxf(num_format_str='ddd d mmm yyyy hh:mm:ss')
            odd_default_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue')
            odd_text_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue', num_format_str='@')
            odd_date_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue', num_format_str='ddd d mmm yyyy hh:mm:ss')
            workbook = xlwt.Workbook()
            worksheet = workbook.add_sheet('OC110')
            row = 0
            if dialog.header_row:
                for col, heading in enumerate((
                    'Serial',
                    'ID',
                    'Start',
                    'Finish',
                    'Mode',
                    'Bottle Vol',
                    'Sample Vol',
                    'Dilution',
                    'Heads',
                    )):
                    worksheet.write(row, col, heading, header_style)
                row += 1
                # Freeze the header row at the top of the sheet
                worksheet.panes_frozen = True
                worksheet.horz_split_pos = 1
            for bottle in self.parent.data_logger.bottles:
                if dialog.row_colors:
                    (default_style, text_style, date_style) = [
                        (even_default_style, even_text_style, even_date_style),
                        (odd_default_style, odd_text_style, odd_date_style)
                        ][row % 2]
                else:
                    (default_style, text_style, date_style) = (
                        even_default_style, even_text_style, even_date_style
                        )
                data = (
                    bottle.serial,
                    bottle.id,
                    bottle.start,
                    bottle.finish,
                    bottle.mode_string,
                    bottle.bottle_volume,
                    bottle.sample_volume,
                    bottle.dilution,
                    len(bottle.heads),
                    )
                for col, value in enumerate(data):
                    if isinstance(value, datetime):
                        worksheet.write(row, col, value, date_style)
                    elif isinstance(value, basestring):
                        worksheet.write(row, col, value, text_style)
                    else:
                        worksheet.write(row, col, value, default_style)
                row += 1
            worksheet.col(1).width = 4 * 256
            worksheet.col(2).width = 24 * 256
            worksheet.col(3).width = 24 * 256
            workbook.save(filename)


