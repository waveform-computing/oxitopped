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

"""Module implementing the oxitopview bottle sub-window."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import io
import os
from datetime import datetime
from itertools import izip_longest

import numpy as np
from PyQt4 import QtCore, QtGui, uic

from oxitopped.windows import get_ui_file
from oxitopped.windows.exporter import BaseExporter
from oxitopped.windows.export_csv_dialog import ExportCsvDialog
from oxitopped.windows.export_excel_dialog import ExportExcelDialog
from oxitopped.bottles import DataAnalyzer

# XXX Py3
try:
    basestring
except NameError:
    basestring = str

try:
    import matplotlib
    from matplotlib.dates import DateFormatter
    from matplotlib.figure import Figure
    from matplotlib.colors import colorConverter
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    matplotlib = None


class BottleWindow(QtGui.QWidget):
    "Document window for displaying a particular bottle"

    def __init__(self, bottle):
        super(BottleWindow, self).__init__(None)
        self.ui = uic.loadUi(get_ui_file('bottle_window.ui'), self)
        self.ui.readings_view.setModel(BottleModel(DataAnalyzer(bottle, delta=True)))
        for col in range(self.ui.readings_view.model().columnCount()):
            self.ui.readings_view.resizeColumnToContents(col)
        self.exporter = BottleExporter(self)
        if matplotlib:
            self.figure = Figure(figsize=(5.0, 5.0), facecolor='w', edgecolor='w')
            self.canvas = FigureCanvas(self.figure)
            self.axes = self.figure.add_subplot(111)
            self.ui.splitter.addWidget(self.canvas)
            self.redraw_timer = QtCore.QTimer()
            self.redraw_timer.setInterval(200) # msecs
            self.redraw_timer.timeout.connect(self.redraw_timeout)
            self.ui.splitter.splitterMoved.connect(self.splitter_moved)
        self.refresh_edits()
        self.setWindowTitle('Bottle %s' % bottle.serial)
        self.ui.absolute_check.toggled.connect(self.absolute_toggled)
        self.ui.points_spin.valueChanged.connect(self.points_changed)

    @property
    def model(self):
        return self.ui.readings_view.model()

    @property
    def bottle(self):
        return self.model.analyzer.bottle

    def refresh_window(self):
        "Forces the list to be re-read from the data logger"
        self.model.beginResetModel()
        self.model.analyzer.refresh()
        self.refresh_edits()
        self.model.endResetModel()

    def refresh_edits(self):
        "Refresh all the edit controls from the bottle"
        bottle = self.model.analyzer.bottle
        self.ui.bottle_serial_edit.setText(bottle.serial)
        self.ui.bottle_id_edit.setText(str(bottle.id))
        self.ui.measurement_mode_edit.setText(bottle.mode_string)
        self.ui.bottle_volume_spin.setValue(bottle.bottle_volume)
        self.ui.sample_volume_spin.setValue(bottle.sample_volume)
        self.ui.dilution_spin.setValue(bottle.dilution)
        self.ui.start_timestamp_edit.setText(bottle.start.strftime('%c'))
        self.ui.finish_timestamp_edit.setText(bottle.finish.strftime('%c'))
        self.ui.measurement_complete_edit.setText(bottle.completed)
        self.ui.desired_values_edit.setText(str(bottle.expected_measurements))
        self.ui.actual_values_edit.setText(str(bottle.actual_measurements))
        self.ui.points_spin.setMaximum(
            max(1, bottle.actual_measurements - (
                1 if bottle.actual_measurements % 2 == 0 else 0)))
        self.ui.points_spin.setEnabled(bottle.actual_measurements > 1)
        self.ui.absolute_check.setEnabled(bottle.actual_measurements > 1)
        if bottle.actual_measurements > 1:
            self.canvas.show()
            self.invalidate_graph()
        else:
            self.canvas.hide()

    def export_file(self):
        "Export the readings to a user-specified filename"
        self.exporter.export_file()

    def absolute_toggled(self, checked):
        "Handler for the toggled signal of the absolute_check control"
        self.model.delta = not checked
        if matplotlib:
            self.invalidate_graph()

    def points_changed(self, value):
        "Handler for the valueChanged signal of the points_spin control"
        self.model.points = value
        if matplotlib:
            self.invalidate_graph()

    def splitter_moved(self, pos, index):
        "Handler for the moved signal of the splitter control"
        self.invalidate_graph()

    def invalidate_graph(self):
        "Invalidate the matplotlib graph on a timer"
        if self.redraw_timer.isActive():
            self.redraw_timer.stop()
        self.redraw_timer.start()

    def redraw_timeout(self):
        "Handler for the redraw_timer's timeout event"
        self.redraw_timer.stop()
        self.redraw_figure()

    def redraw_figure(self):
        "Called to redraw the channel image"
        # Configure the x and y axes appearance
        self.axes.clear()
        self.axes.set_frame_on(True)
        self.axes.set_axis_on()
        self.axes.grid(True)
        self.axes.set_xlabel(self.tr('Time'))
        if self.ui.absolute_check.isChecked():
            self.axes.set_ylabel(self.tr('Pressure (hPa)'))
        else:
            self.axes.set_ylabel(self.tr('Delta Pressure (hPa)'))
        m = self.ui.points_spin.value()
        for head_ix, head in enumerate(self.model.analyzer.heads):
            self.axes.plot_date(
                x=self.model.analyzer.timestamps,
                y=head,
                fmt='%s-' % matplotlib.rcParams['axes.color_cycle'][
                    head_ix % len(matplotlib.rcParams['axes.color_cycle'])]
                )
        self.axes.xaxis.set_major_formatter(DateFormatter('%d %b'))
        self.axes.autoscale_view()
        self.canvas.draw()


class BottleModel(QtCore.QAbstractTableModel):
    def __init__(self, analyzer):
        super(BottleModel, self).__init__()
        self.analyzer = analyzer

    def _get_points(self):
        return self.analyzer.points

    def _set_points(self, value):
        if value != self.analyzer.points:
            self.beginResetModel()
            try:
                self.analyzer.points = value
            finally:
                self.endResetModel()

    points = property(_get_points, _set_points)

    def _get_delta(self):
        return self.analyzer.delta

    def _set_delta(self, value):
        if value != self.analyzer.delta:
            first = self.index(0, 3)
            last = self.index(self.rowCount() - 1, self.columnCount() - 1)
            self.analyzer.delta = value
            self.dataChanged.emit(first, last)

    delta = property(_get_delta, _set_delta)

    def rowCount(self, parent=None):
        if parent is None:
            parent = QtCore.QModelIndex()
        if parent.isValid():
            return 0
        return len(self.analyzer.timestamps)

    def columnCount(self, parent=None):
        if parent is None:
            parent = QtCore.QModelIndex()
        if parent.isValid():
            return 0
        return len(self.analyzer.bottle.heads) + 3

    def data(self, index, role):
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole:
            return None
        if index.column() == 0:
            return index.row()
        elif index.column() == 1:
            return self.analyzer.timestamps[index.row()].strftime('%c')
        elif index.column() == 2:
            return str(self.analyzer.timestamps[index.row()] - self.analyzer.bottle.start)
        else:
            head = self.analyzer.heads[index.column() - 3]
            if index.row() < len(head):
                return '%.6g' % head[index.row()]
            else:
                return ''

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            columns = [
                'No.',
                'Timestamp',
                'Offset',
                ] + ['Head %s' % head.serial for head in self.analyzer.bottle.heads]
            return columns[section]
        elif (orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.ForegroundRole
                and section >= 3 and matplotlib):
            return QtGui.QBrush(QtGui.QColor(*(i * 255 for i in colorConverter.to_rgb(
                matplotlib.rcParams['axes.color_cycle'][
                    (section - 3) % len(matplotlib.rcParams['axes.color_cycle'])]))))
        elif orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return section


class BottleExporter(BaseExporter):
    "Data exporter class for bottle readings"

    def __init__(self, parent):
        super(BottleExporter, self).__init__(parent)
        self.title = self.parent.tr('Export bottle readings')

    def export_csv(self, filename):
        "Export the bottle readings to a CSV file"
        dialog = ExportCsvDialog(self.parent)
        if dialog.exec_():
            from oxitopped.export_csv import CsvExporter
            exporter = CsvExporter()
            exporter.delimiter = dialog.delimiter
            exporter.lineterminator = dialog.lineterminator
            exporter.quotechar = dialog.quotechar
            exporter.quoting = dialog.quoting
            exporter.header_row = dialog.header_row
            exporter.timestamp_format = dialog.timestamp_format
            exporter.export_bottle(
                filename,
                self.parent.model.analyzer.bottle,
                delta=self.parent.model.delta,
                points=self.parent.model.points)

    def export_excel(self, filename):
        "Export the bottle list to an Excel file"
        dialog = ExportExcelDialog(self.parent)
        if dialog.exec_():
            from oxitopped.export_xls import ExcelExporter
            exporter = ExcelExporter()
            exporter.header_row = dialog.header_row
            exporter.row_colors = dialog.row_colors
            exporter.export_bottle(
                filename,
                self.parent.model.analyzer.bottle,
                delta=self.parent.model.delta,
                points=self.parent.model.points)

