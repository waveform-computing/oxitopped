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

"""
This module provides an implementation of PEP3143, the python daemon
specification.  If the python-daemon package is available, the fully functional
DaemonContext class from that package is imported and made available.
Otherwise, a dummy class which simply runs a console application in the
foreground with no daemon features is provided.
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import os
import signal

try:
    from daemon import DaemonContext
except ImportError:
    class DaemonContext(object):
        """
        Dummy DaemonContext used when python-daemon package is not available.
        Does not support running as an attached daemon; simply provides a call
        compatible API (mostly) for foreground running.
        """
        def __init__(
                self, files_preserve=None, chroot_directory=None,
                working_directory='/', umask=0, pidfile=None,
                detach_process=False, signal_map=None,
                uid=os.getuid(), gid=os.getgid(),
                prevent_core=True, stdin=None, stdout=None, stderr=None):
            super(DaemonContext, self).__init__()
            assert detach_process==False
            assert not chroot_directory
            assert uid==os.getuid()
            assert gid==os.getgid()
            os.chdir(working_directory)
            os.umask(umask)
            self._pidfile = None
            self.pidfile = pidfile
            self.saved_signals = {}
            self.signal_map = {}
            if signal_map:
                for signum, handler in signal_map.items():
                    self.saved_signals[signum] = signal.signal(signum, handler)
                self.signal_map = signal_map

        def handle(self, signum, frame):
            if signum in self.signal_map:
                self.signal_map(signum, frame)
            if signum in self.saved_signals:
                self.saved_signals(signum, frame)

        def open(self):
            if self.pidfile:
                self._pidfile = self.pidfile.__enter__()

        def close(self):
            if self._pidfile:
                self._pidfile.__exit__(None, None, None)

        def __enter__(self):
            self.open()
            return self

        def __exit__(self, type, value, traceback):
            self.close()
            return False

