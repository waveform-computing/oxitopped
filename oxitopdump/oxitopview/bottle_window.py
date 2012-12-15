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

from PyQt4 import QtCore, QtGui, uic


MODULE_DIR = os.path.abspath(os.path.dirname(__file__))


class BottleModel(QtCore.QAbstractTableModel):
    def __init__(self, bottle, delta=True):
        super(BottleModel, self).__init__()
        self.bottle = bottle
        self.delta = delta

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return max(len(head.readings) for head in self.bottle.heads)

    def columnCount(self, parent):
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
                if self.delta:
                    if index.row() == 0:
                        return '0'
                    else:
                        return str(
                            head.readings[index.row()] -
                            head.readings[0])
                else:
                    return str(head.readings[index.row()])
            else:
                return ''

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            columns = [
                'No.',
                'Timestamp',
                'Offset',
                ] + [head.serial for head in self.bottle.heads]
            return columns[section]
        elif orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return section
        else:
            return None


class BottleWindow(QtGui.QWidget):
    "Document window for displaying a particular bottle"

    def __init__(self, bottle):
        super(BottleWindow, self).__init__(None)
        print(bottle.interval)
        self.ui = uic.loadUi(
            os.path.join(MODULE_DIR, 'bottle_window.ui'), self)
        self.ui.bottle_serial_edit.setText(bottle.serial)
        self.ui.bottle_id_edit.setText(str(bottle.id))
        self.ui.measurement_mode_edit.setText(
            'Pressure %dd' % (bottle.finish - bottle.start).days
                if bottle.mode == 'pressure' else
            'BOD'
                if bottle.mode == 'bod' else
            'Unknown'
            )
        self.ui.bottle_volume_edit.setText('%.1fml' % bottle.bottle_volume)
        self.ui.sample_volume_edit.setText('%.1fml' % bottle.sample_volume)
        self.ui.start_timestamp_edit.setText(bottle.start.strftime('%c'))
        self.ui.finish_timestamp_edit.setText(bottle.finish.strftime('%c'))
        self.ui.measurement_complete_edit.setText = (
            'Yes' if bottle.finish < datetime.now() else 'No')
        self.ui.desired_values_edit.setText(str(bottle.measurements))
        self.ui.actual_values_edit.setText(str(
            max(len(head.readings) for head in bottle.heads)))
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            try:
                self.ui.readings_view.setModel(BottleModel(bottle))
                self.setWindowTitle('Bottle %s' % bottle.serial)
            except (ValueError, IOError) as exc:
                QtGui.QMessageBox.critical(self, self.tr('Error'), str(exc))
                self.close()
                return
        finally:
            QtGui.QApplication.instance().restoreOverrideCursor()


