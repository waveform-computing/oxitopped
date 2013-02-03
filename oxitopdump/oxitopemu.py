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

"""An OxiTop OC110 emulator.

This application emulates an OxiTop OC110 data logger for the purposes of
easy development without access to an actual OC110.

"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import os
import logging

import serial

from oxitopdump import Application
from oxitopdump.bottles import DummyLogger


class EmuApplication(Application):
    """
    %prog [options]

    This utility dumps the sample readings stored on a connected OxiTop Data
    Logger to files in CSV or Excel format. If bottle-serial values are
    specified, the details of those bottles and all heads attached to them will
    be exported, otherwise a list of all available bottles is exported.
    The bottle-serial values may include *, ?, and [] wildcards. The filename
    value may include references to bottle attributes like {bottle.serial} or
    {bottle.id}.
    """

    def main(self, options, args):
        if options.port == 'TEST':
            # XXX Can we get this working with stdin/stdout?
            pass
        else:
            dummy_logger = DummyLogger(serial.Serial(
                options.port, baudrate=9600, bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                timeout=5, rtscts=True))
        try:
            dummy_logger.join()
        except:
            dummy_logger.terminated = True


main = EmuApplication()

