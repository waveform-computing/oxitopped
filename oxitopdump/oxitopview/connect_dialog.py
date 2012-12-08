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

"""Module implementing the oxitopview connect dialog."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os

from PyQt4 import QtCore, QtGui, uic


class ConnectDialog(QtGui.QDialog):
    "Implements the file/connect dialog"

    def __init__(self, parent=None):
        super(ConnectDialog, self).__init__(parent)
        self.ui = uic.loadUi(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    'connect_dialog.ui'
                )), self)
        # Read the last-used lists
        self.settings = self.parent().settings
        self.settings.beginGroup('last_used')
        try:
            count = self.settings.beginReadArray('com_ports')
            try:
                for i in range(count):
                    self.settings.setArrayIndex(i)
                    self.ui.com_port_combo.addItem(
                        self.settings.value('port'))
            finally:
                self.settings.endArray()
            self.ui.com_port_combo.setEditText(
                self.settings.value('com_port', ''))
        finally:
            self.settings.endGroup()
        # Connect up signals
        self.ui.com_port_combo.editTextChanged.connect(self.com_port_changed)
        self.com_port_changed()

    def accept(self):
        "Called when the user closes the dialog to open a file"
        super(ConnectDialog, self).accept()
        # When the dialog is accepted insert the current filenames at the top
        # of the combos or, if the entry already exists, move it to the top of
        # the combo list
        i = self.ui.com_port_combo.findText(
            self.ui.com_port_combo.currentText())
        if i == -1:
            self.ui.com_port_combo.addItem(
                self.ui.com_port_combo.currentText())
        else:
            self.ui.com_port_combo.insertItem(
                0, self.ui.com_port_combo.currentText())
            self.ui.com_port_combo.setCurrentIndex(0)
            self.ui.com_port_combo.removeItem(i + 1)
        # Keep the drop-downs to a reasonable size
        while self.ui.com_port_combo.count() > self.ui.com_port_combo.maxCount():
            self.ui.com_port_combo.removeItem(
                self.ui.com_port_combo.count() - 1)
        # Only write the last-used lists when the dialog is accepted (not when
        # cancelled or just closed)
        self.settings.beginGroup('last_used')
        try:
            self.settings.beginWriteArray(
                'com_ports', self.ui.com_port_combo.count())
            try:
                for i in range(self.ui.com_port_combo.count()):
                    self.settings.setArrayIndex(i)
                    self.settings.setValue(
                        'port', self.ui.com_port_combo.itemText(i))
            finally:
                self.settings.endArray()
            self.settings.setValue(
                'com_port', self.ui.com_port_combo.currentText())
        finally:
            self.settings.endGroup()

    @property
    def com_port(self):
        "Returns the current content of the data_file combo"
        result = str(self.ui.com_port_combo.currentText())
        if result:
            return result
        else:
            return None

    def com_port_changed(self, value=None):
        "Called to update the dialog buttons when the data_file changes"
        if value is None:
            value = self.ui.com_port_combo.currentText()
        self.ui.button_box.button(
            QtGui.QDialogButtonBox.Ok).setEnabled(value != '')

