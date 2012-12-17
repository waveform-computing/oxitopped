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

import io
import os
from datetime import datetime

import numpy as np
from PyQt4 import QtCore, QtGui, uic

from oxitopdump.oxitopview.exporter import BaseExporter
from oxitopdump.oxitopview.export_csv_dialog import ExportCsvDialog
from oxitopdump.oxitopview.export_excel_dialog import ExportExcelDialog

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
    from collections import deque
    from itertools import islice
except ImportError:
    matplotlib = None


MODULE_DIR = os.path.abspath(os.path.dirname(__file__))


def moving_average(iterable, n):
    "Calculates a moving average of iterable over n elements"
    it = iter(iterable)
    d = deque(islice(it, n - 1))
    d.appendleft(0.0)
    s = sum(d)
    for elem in it:
        s += elem - d.popleft()
        d.append(elem)
        yield s / n


class BottleWindow(QtGui.QWidget):
    "Document window for displaying a particular bottle"

    def __init__(self, bottle):
        super(BottleWindow, self).__init__(None)
        self.ui = uic.loadUi(
            os.path.join(MODULE_DIR, 'bottle_window.ui'), self)
        self.ui.readings_view.setModel(BottleModel(bottle))
        for col in range(self.ui.readings_view.model().columnCount()):
            self.ui.readings_view.resizeColumnToContents(col)
        self.exporter = BottleExporter(self)
        self.refresh_edits()
        self.setWindowTitle('Bottle %s' % bottle.serial)
        self.ui.absolute_check.toggled.connect(self.absolute_toggled)
        self.ui.average_spin.valueChanged.connect(self.average_changed)
        if matplotlib:
            self.figure = Figure(figsize=(5.0, 5.0), facecolor='w', edgecolor='w')
            self.canvas = FigureCanvas(self.figure)
            self.axes = self.figure.add_axes((0.1, 0.1, 0.8, 0.8))
            self.ui.splitter.addWidget(self.canvas)
            self.redraw_timer = QtCore.QTimer()
            self.redraw_timer.setInterval(200) # msecs
            self.redraw_timer.timeout.connect(self.redraw_timeout)
            self.ui.splitter.splitterMoved.connect(self.splitter_moved)
            self.invalidate_graph()

    @property
    def bottle(self):
        return self.ui.readings_view.model().bottle

    def refresh_window(self):
        "Forces the list to be re-read from the data logger"
        model = self.ui.readings_view.model()
        first = model.index(0, 0)
        last = model.index(model.rowCount() - 1, model.columnCount() - 1)
        model.bottle.refresh()
        self.refresh_edits()
        model.dataChanged.emit(first, last)

    def refresh_edits(self):
        "Refresh all the edit controls from the bottle"
        bottle = self.ui.readings_view.model().bottle
        self.ui.bottle_serial_edit.setText(bottle.serial)
        self.ui.bottle_id_edit.setText(str(bottle.id))
        self.ui.measurement_mode_edit.setText(bottle.mode_string)
        self.ui.bottle_volume_spin.setValue(bottle.bottle_volume)
        self.ui.sample_volume_spin.setValue(bottle.sample_volume)
        self.ui.dilution_edit.setText('1+%d' % bottle.dilution)
        self.ui.start_timestamp_edit.setText(bottle.start.strftime('%c'))
        self.ui.finish_timestamp_edit.setText(bottle.finish.strftime('%c'))
        self.ui.measurement_complete_edit.setText(
            'Yes' if bottle.finish < datetime.now() else 'No')
        self.ui.desired_values_edit.setText(str(bottle.measurements))
        self.ui.actual_values_edit.setText(str(
            max(len(head.readings) for head in bottle.heads)))

    def export_file(self):
        "Export the readings to a user-specified filename"
        self.exporter.export_file()

    def absolute_toggled(self, checked):
        "Handler for the toggled signal of the absolute_check control"
        self.ui.readings_view.model().delta = not checked
        if matplotlib:
            self.invalidate_graph()

    def average_changed(self, value):
        "Handler for the valueChanged signal of the average_spin control"
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
        m = self.ui.average_spin.value()
        for head_ix, head in enumerate(self.bottle.heads):
            self.axes.plot_date(
                x=[
                    self.bottle.start + (self.bottle.interval * (reading + m - 1))
                    for reading in range(len(head.readings) - (m - 1))
                    ],
                y=list(moving_average((
                    reading - (head.readings[0] if self.ui.readings_view.model().delta else 0)
                    for reading in head.readings
                    ), m)),
                fmt='%s-' % matplotlib.rcParams['axes.color_cycle'][
                    head_ix % len(matplotlib.rcParams['axes.color_cycle'])]
                )
        self.axes.xaxis.set_major_formatter(DateFormatter('%d %b'))
        self.axes.autoscale_view()
        self.canvas.draw()


class BottleModel(QtCore.QAbstractTableModel):
    def __init__(self, bottle, delta=True):
        super(BottleModel, self).__init__()
        self.bottle = bottle
        self._delta = delta

    def _get_delta(self):
        return self._delta

    def _set_delta(self, value):
        if value != self._delta:
            self._delta = bool(value)
            first = self.index(0, 3)
            last = self.index(self.rowCount() - 1, self.columnCount() - 1)
            self.dataChanged.emit(first, last)

    delta = property(_get_delta, _set_delta)

    def rowCount(self, parent=None):
        if parent is None:
            parent = QtCore.QModelIndex()
        if parent.isValid():
            return 0
        return max(len(head.readings) for head in self.bottle.heads)

    def columnCount(self, parent=None):
        if parent is None:
            parent = QtCore.QModelIndex()
        if parent.isValid():
            return 0
        return len(self.bottle.heads) + 3

    def data(self, index, role):
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole:
            return None
        if index.column() == 0:
            return index.row()
        elif index.column() == 1:
            return (self.bottle.start + (self.bottle.interval * index.row())).strftime('%c')
        elif index.column() == 2:
            return str(self.bottle.interval * index.row())
        else:
            head = self.bottle.heads[index.column() - 3]
            if index.row() < len(head.readings):
                return str(head.readings[index.row()] - (head.readings[0] if self.delta else 0))
            else:
                return ''

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            columns = [
                'No.',
                'Timestamp',
                'Offset',
                ] + ['Head %s' % head.serial for head in self.bottle.heads]
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
            import csv
            bottle = self.parent.bottle
            delta = self.parent.ui.readings_view.model().delta
            with io.open(filename, 'wb') as output_file:
                writer = csv.writer(output_file,
                    delimiter=dialog.delimiter,
                    lineterminator=dialog.lineterminator,
                    quotechar=dialog.quotechar,
                    quoting=dialog.quoting,
                    doublequote=csv.excel.doublequote)
                if dialog.header_row:
                    writer.writerow([
                        'No.',
                        'Timestamp',
                        'Offset',
                        ] + [
                        'Head %s' % head.serial
                        for head in bottle.heads
                        ])
                for reading in range(
                        max(len(head.readings)
                        for head in bottle.heads)):
                    row = [
                        reading,
                        (bottle.start + (bottle.interval * reading)).strftime(dialog.timestamp_format),
                        str(bottle.interval * reading),
                        ] + [
                        head.readings[reading] - (head.readings[0] if delta else 0)
                            if reading < len(head.readings) else None
                        for head in bottle.heads
                        ]
                    writer.writerow(row)

    def export_excel(self, filename):
        "Export the bottle list to an Excel file"
        dialog = ExportExcelDialog(self.parent)
        if dialog.exec_():
            import xlwt
            bottle = self.parent.bottle
            delta = self.parent.ui.readings_view.model().delta
            header_style = xlwt.easyxf('font: bold on')
            even_default_style = xlwt.easyxf('')
            even_text_style = xlwt.easyxf(num_format_str='@')
            even_date_style = xlwt.easyxf(num_format_str='ddd d mmm yyyy hh:mm:ss')
            odd_default_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue')
            odd_text_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue', num_format_str='@')
            odd_date_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue', num_format_str='ddd d mmm yyyy hh:mm:ss')
            workbook = xlwt.Workbook()
            # Create the bottle details sheet
            worksheet = workbook.add_sheet('Bottle %s' % bottle.serial)
            data = (
                ('Bottle Serial',         bottle.serial),
                ('Bottle ID',             bottle.id),
                ('Bottle Volume',         bottle.bottle_volume),
                ('Sample Volume',         bottle.sample_volume),
                ('Dilution',              '1+%d' % bottle.dilution),
                ('Measurement Mode',      bottle.mode_string),
                ('Measurement Complete',  bottle.finish < datetime.now()),
                ('Start Timestamp',       bottle.start),
                ('Finish Timestamp',      bottle.finish),
                ('Desired no. of Values', bottle.measurements),
                ('Actual no. of Values',  max(len(head.readings) for head in bottle.heads)),
                )
            for row, row_data in enumerate(data):
                for col, value in enumerate(row_data):
                    if col == 0:
                        worksheet.write(row, col, value, header_style)
                    elif isinstance(value, datetime):
                        worksheet.write(row, col, value, even_date_style)
                    elif isinstance(value, basestring):
                        worksheet.write(row, col, value, even_text_style)
                    else:
                        worksheet.write(row, col, value, even_default_style)
            worksheet.col(0).width = 22 * 256
            worksheet.col(1).width = 24 * 256
            # Create the bottle readings sheet
            worksheet = workbook.add_sheet('Readings')
            row = 0
            if dialog.header_row:
                data = [
                    'No.',
                    'Timestamp',
                    'Offset',
                    ] + [
                    'Head %s' % head.serial
                    for head in bottle.heads
                    ]
                for col, value in enumerate(data):
                    worksheet.write(row, col, value, header_style)
                row += 1
                # Freeze the header row at the top of the sheet
                worksheet.panes_frozen = True
                worksheet.horz_split_pos = 1
            for reading in range(
                    max(len(head.readings)
                    for head in bottle.heads)):
                if dialog.row_colors:
                    (default_style, text_style, date_style) = [
                        (even_default_style, even_text_style, even_date_style),
                        (odd_default_style, odd_text_style, odd_date_style)
                        ][row % 2]
                else:
                    (default_style, text_style, date_style) = (
                        even_default_style, even_text_style, even_date_style
                        )
                data = [
                    reading,
                    bottle.start + bottle.interval * reading,
                    str(bottle.interval * reading),
                    ] + [
                    head.readings[reading] - (head.readings[0] if delta else 0)
                        if reading < len(head.readings) else None
                    for head in bottle.heads
                    ]
                for col, value in enumerate(data):
                    if isinstance(value, datetime):
                        worksheet.write(row, col, value, date_style)
                    elif isinstance(value, basestring):
                        worksheet.write(row, col, value, text_style)
                    else:
                        worksheet.write(row, col, value, default_style)
                row += 1
            worksheet.col(0).width = 4 * 256
            worksheet.col(1).width = 24 * 256
            worksheet.col(2).width = 24 * 256
            workbook.save(filename)


