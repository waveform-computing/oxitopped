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

"""Module implementing the oxitopview data logger window."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os

from PyQt4 import QtCore, QtGui, uic


MODULE_DIR = os.path.abspath(os.path.dirname(__file__))


class DataLoggerModel(QtCore.QAbstractTableModel):
    def __init__(self, data_logger):
        super(DataLoggerModel, self).__init__()
        self.data_logger = data_logger

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.data_logger.bottles)

    def columnCount(self, parent):
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
            'Pressure %dd' % bottle.pressure,
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
        else:
            return None


class DataLoggerWindow(QtGui.QWidget):
    "Document window for the data logger connection"

    def __init__(self, data_logger):
        super(DataLoggerWindow, self).__init__(None)
        self.ui = uic.loadUi(
            os.path.join(MODULE_DIR, 'data_logger_window.ui'), self)
        try:
            self.ui.bottles_view.setModel(DataLoggerModel(data_logger))
            self.setWindowTitle(
                '%s on %s' % (data_logger.id, data_logger.port.port))
        except (ValueError, IOError) as exc:
            QtGui.QMessageBox.critical(self, self.tr('Error'), str(exc))
            self.close()
            return

