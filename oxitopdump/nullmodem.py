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
Defines a NullModem class for emulating serial interfaces between applications.
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import time
from collections import deque
from threading import Condition

import serial


def null_modem(
        baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE, timeout=None, xonxoff=False,
        rtscts=False, writeTimeout=None, dsrdtr=False, interCharTimeout=None):
    """
    Construct both ends of a null-modem cable, returning a tuple of two serial
    ports. All parameters are the same as the pyserial Serial class.
    """
    port1 = NullModem(
            'DTE', baudrate, bytesize, parity, stopbits, timeout,
            xonxoff, rtscts, writeTimeout, dsrdtr, interCharTimeout
            )
    port2 = NullModem(
            'DCE', baudrate, bytesize, parity, stopbits, timeout,
            xonxoff, rtscts, writeTimeout, dsrdtr, interCharTimeout
            )
    port1._other = port2
    port2._other = port1
    return (port1, port2)


class NullModem(object):
    """
    Emulates one end of a null modem. Don't construct this class directly, but
    use the null_modem routine below to construct both ends of the null-modem.
    All parameters are equivalent to the pyserial Serial class.

    Note: do not instantiate this class directly; use the `null_modem` function
    to instantiate two at once and associate each with the other.
    """

    def __init__(self, port=None, baudrate=9600, bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            timeout=None, xonxoff=False, rtscts=False, writeTimeout=None,
            dsrdtr=False, interCharTimeout=None):
        super(NullModem, self).__init__()
        self.port = port
        self.name = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.dsrdtr = dsrdtr
        self.writeTimeout = writeTimeout
        self.interCharTimeout = interCharTimeout
        self._other = None
        self._rts = False
        self._lock = Condition()
        self._buf = deque()
        self._opened = False
        if self.port:
            self.open()

    def readable(self):
        return True

    def writeable(self):
        return True

    def seekable(self):
        return False

    def open(self):
        assert not self._opened
        self.flushInput()
        self._opened = True

    def close(self):
        assert self._opened
        self.setRTS(False)
        self.flushInput()
        self._opened = False

    def isOpen(self):
        return self._opened

    def flush(self):
        pass

    def flushInput(self):
        with self._lock:
            self._buf = deque()

    def flushOutput(self):
        pass

    def nonblocking(self):
        raise NotImplementedError

    def fileno(self):
        raise NotImplementedError

    def setXON(self, level=True):
        raise NotImplementedError

    def sendBreak(self, duration=0.25):
        raise NotImplementedError

    def setBreak(self, level=True):
        raise NotImplementedError

    def setRTS(self, level=True):
        self._rts = level

    def getCTS(self):
        result = self._other._rts
        return result

    def setDTR(self, level=True):
        if self.dsrdtr is None:
            # DTR/DSR follows RTS/CTS
            self.setRTS(level)

    def getDSR(self):
        if self.dsrdtr is None:
            # DTR/DSR follows RTS/CTS
            return self.getCTS()
        return False

    def getCD(self):
        if self.dsrdtr is None:
            # DTR/DSR follows RTS/CTS
            return self.getCTS()
        return False

    def getRI(self):
        raise NotImplementedError

    def readinto(self, b):
        # XXX Should implement this from read()
        raise NotImplementedError

    def inWaiting(self):
        with self._lock:
            return len(self._buf)

    def read(self, size=1):
        assert self._opened
        start = time.time()
        result = b''
        while len(result) < size and (
                self.timeout is None or time.time() < start + self.timeout):
            with self._lock:
                if self._buf:
                    result += self._buf.popleft()
                else:
                    self._lock.wait(0.1)
        assert len(result) <= size
        return result

    def write(self, data):
        assert self._opened
        for byte in data:
            with self._other._lock:
                if self._other._opened:
                    self._other._buf.append(byte)
                    self._other._lock.notify()
            # Pause for the amount of time it would take to send data
            time.sleep(10.0 / self.baudrate)
        return len(data)


