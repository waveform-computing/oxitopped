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

from PyQt4 import QtCore, QtGui, uic

from oxitopdump.oxitopview.connect_dialog import ConnectDialog
from oxitopdump.oxitopview.data_logger_window import DataLoggerWindow


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
        self.ui.x_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.x_label)
        self.ui.y_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.y_label)
        self.ui.value_label = QtGui.QLabel('')
        self.statusBar().addWidget(self.ui.value_label)
        # Connect up signals to methods
        self.ui.mdi_area.subWindowActivated.connect(self.window_changed)
        self.ui.quit_action.setIcon(get_icon('application-exit'))
        self.ui.about_action.triggered.connect(self.about)
        self.ui.about_action.setIcon(get_icon('help-about'))
        self.ui.about_qt_action.triggered.connect(self.about_qt)
        self.ui.about_qt_action.setIcon(get_icon('help-about'))
        self.ui.connect_action.setIcon(get_icon('document-open'))
        self.ui.connect_action.triggered.connect(self.open_file)
        self.ui.close_action.setIcon(get_icon('window-close'))
        self.ui.close_action.triggered.connect(self.close_file)
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
        super(MainWindow, self).close()
        self.settings.beginGroup('main_window')
        try:
            self.settings.setValue('size', self.size())
            self.settings.setValue('position', self.pos())
        finally:
            self.settings.endGroup()

    def connect_logger(self):
        "Handler for the File/Connect action"
        dialog = ConnectDialog(self)
        if dialog.exec_():
            window = None
            try:
                window = self.ui.mdi_area.addSubWindow(
                    DataLoggerWindow(dialog.com_port))
                window.show()
            except KeyboardInterrupt:
                if window is not None:
                    window.close()

    def close_file(self):
        "Handler for the File/Close action"
        self.ui.mdi_area.currentSubWindow().close()

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
        #self.ui.export_document_action.setEnabled(self.sub_widget is not None)
