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

"""Module implementing the oxitopview main window."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import logging

import serial
from PyQt4 import QtCore, QtGui, uic

from oxitopdump.oxitopview.connect_dialog import ConnectDialog
from oxitopdump.oxitopview.data_logger_window import DataLoggerWindow
from oxitopdump.bottles import DataLogger, DummyLogger, null_modem



MODULE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_icon(icon_id):
    "Returns an icon from the system theme or our fallback theme if required"
    return QtGui.QIcon.fromTheme(icon_id,
        QtGui.QIcon(os.path.join(
            MODULE_DIR, 'fallback-theme', icon_id + '.png')))


class MainWindow(QtGui.QMainWindow):
    "The oxitopview main window"

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.dummy_logger = None
        self.ui = uic.loadUi(os.path.join(MODULE_DIR, 'main_window.ui'), self)
        # Read configuration
        self.settings = QtCore.QSettings()
        self.settings.beginGroup('main_window')
        try:
            self.resize(
                self.settings.value(
                    'size', QtCore.QSize(640, 480)))
            self.move(
                self.settings.value(
                    'position', QtCore.QPoint(100, 100)))
        finally:
            self.settings.endGroup()
        # Configure status bar elements
        self.ui.progress_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.progress_label)
        self.progress_index = 0
        # Connect up signals to methods
        self.ui.mdi_area.subWindowActivated.connect(self.window_changed)
        self.ui.quit_action.setIcon(get_icon('application-exit'))
        self.ui.about_action.triggered.connect(self.about)
        self.ui.about_action.setIcon(get_icon('help-about'))
        self.ui.about_qt_action.triggered.connect(self.about_qt)
        self.ui.about_qt_action.setIcon(get_icon('help-about'))
        self.ui.connect_action.setIcon(get_icon('document-open'))
        self.ui.connect_action.triggered.connect(self.connect_logger)
        self.ui.close_action.setIcon(get_icon('window-close'))
        self.ui.close_action.triggered.connect(self.close_file)
        self.ui.export_action.setIcon(get_icon('x-office-document'))
        self.ui.export_action.triggered.connect(self.export_file)
        self.ui.refresh_action.setIcon(get_icon('view-refresh'))
        self.ui.refresh_action.triggered.connect(self.refresh_window)
        self.ui.status_bar_action.triggered.connect(self.toggle_status)
        self.ui.view_menu.aboutToShow.connect(self.update_status)

    @property
    def sub_widget(self):
        "Returns the widget shown in the current sub-window"
        if self.ui.mdi_area.currentSubWindow():
            return self.ui.mdi_area.currentSubWindow().widget()
        else:
            return None

    def close(self):
        "Called when the window is closed"
        self.settings.beginGroup('main_window')
        try:
            self.settings.setValue('size', self.size())
            self.settings.setValue('position', self.pos())
        finally:
            self.settings.endGroup()
        if self.dummy_logger:
            self.dummy_logger.terminated = True
            self.dummy_logger = None
        super(MainWindow, self).close()

    def connect_logger(self):
        "Handler for the File/Connect action"
        dialog = ConnectDialog(self)
        if dialog.exec_():
            for window in self.ui.mdi_area.subWindowList():
                if isinstance(window.widget(), DataLoggerWindow) and (
                        window.widget().data_logger.port.port == dialog.com_port):
                    self.ui.mdi_area.setActiveSubWindow(window)
                    return
            window = None
            try:
                if dialog.com_port == 'TEST':
                    data_logger_port, dummy_logger_port = null_modem(
                        baudrate=9600, bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                        timeout=5, rtscts=True)
                    if self.dummy_logger:
                        # If there's a prior instance of dummy logger (the user
                        # has previously opened and closed a TEST window), tell
                        # it to terminate before we replace it
                        self.dummy_logger.terminated = True
                    self.dummy_logger = DummyLogger(dummy_logger_port)
                else:
                    data_logger_port = serial.Serial(
                        dialog.com_port, baudrate=9600, bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                        timeout=5, rtscts=True)
                window = self.ui.mdi_area.addSubWindow(
                    DataLoggerWindow(DataLogger(
                        data_logger_port, progress=(
                            self.progress_start,
                            self.progress_update,
                            self.progress_finish
                            ))))
                window.show()
            except KeyboardInterrupt:
                if window is not None:
                    window.close()

    def close_file(self):
        "Handler for the File/Close action"
        self.ui.mdi_area.currentSubWindow().close()

    def export_file(self):
        "Handler for the File/Export action"
        self.sub_widget.export_file()

    def refresh_window(self):
        "Handler for the View/Refresh action"
        self.sub_widget.refresh_window()

    def update_status(self):
        "Called to update the status_bar_action check state"
        self.ui.status_bar_action.setChecked(self.statusBar().isVisible())

    def toggle_status(self):
        "Handler for the View/Status Bar action"
        if self.statusBar().isVisible():
            self.statusBar().hide()
        else:
            self.statusBar().show()

    def about(self):
        "Handler for the Help/About action"
        QtGui.QMessageBox.about(self,
            str(self.tr('About {}')).format(
                QtGui.QApplication.instance().applicationName()),
            str(self.tr("""\
<b>{application}</b>
<p>Version {version}</p>
<p>{application} is a GUI for interrogating an OxiTop OC110 Data Logger.
Project homepage is at
<a href="https://github.com/waveform80/oxitopdump">https://github.com/waveform80/oxitopdump</a></p>
<p>Copyright 2012 Dave Hughes &lt;dave@waveform.org.uk&gt;</p>""")).format(
                application=QtGui.QApplication.instance().applicationName(),
                version=QtGui.QApplication.instance().applicationVersion(),
            ))

    def about_qt(self):
        "Handler for the Help/About Qt action"
        QtGui.QMessageBox.aboutQt(self, self.tr('About QT'))

    def window_changed(self, window):
        "Called when the MDI child window changes"
        self.update_actions()

    def update_actions(self):
        "Called to update the main window actions"
        self.ui.close_action.setEnabled(self.sub_widget is not None)
        self.ui.export_action.setEnabled(self.sub_widget is not None)
        self.ui.refresh_action.setEnabled(self.sub_widget is not None)

    def progress_start(self):
        QtGui.QApplication.instance().setOverrideCursor(QtCore.Qt.WaitCursor)

    def progress_update(self):
        self.progress_index += 1
        self.ui.progress_label.setText('Communicating' + '.' * (self.progress_index % 8))
        QtGui.QApplication.instance().processEvents()

    def progress_finish(self):
        self.ui.progress_label.setText('')
        QtGui.QApplication.instance().restoreOverrideCursor()

