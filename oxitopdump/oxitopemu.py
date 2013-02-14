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

This application emulates an OxiTop OC110 data dummy_logger for the purposes of
easy development without access to an actual OC110.

"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import io
import sys
import logging
import signal
from xml.etree.ElementTree import fromstring, tostring

import serial

from oxitopdump import Application
from oxitopdump.bottles import Bottle
from oxitopdump.logger import DummyLogger
from oxitopdump.daemon import DaemonContext


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

    def __init__(self):
        super(EmuApplication, self).__init__()
        self.handle_sigint = None
        self.handle_sigterm = None
        self.parser.set_defaults(
            daemon=False,
            )
        self.parser.add_option(
            '-d', '--daemon', dest='daemon', action='store_true',
            help='if specified, start the emulator as a background daemon')

    def main(self, options, args):
        if options.port == 'TEST':
            self.parser.error('Cannot use TEST serial port with the emulator')
        if len(args) != 1:
            self.parser.error('You must specify a bottles definition file')
        with io.open(args[0], 'r') as bottles_file:
            bottles_xml = fromstring(bottles_file.read())
        bottles = [
            Bottle.from_xml(tostring(bottle))
            for bottle in bottles_xml.findall('bottle')
            ]
        logging.info('Opening serial port %s' % options.port)
        port = serial.Serial(
            options.port, baudrate=9600, bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            timeout=5, rtscts=True)
        files_preserve = [port]
        if self.logfile:
            files_preserve.append(self.logfile.stream)
        if not options.daemon:
            files_preserve.append(self.console.stream)
        with DaemonContext(
                files_preserve=files_preserve,
                # The following odd construct is to ensure detachment only
                # where sensible (see default setting of detach_process)
                detach_process=None if options.daemon else False,
                stdout=None if options.daemon else sys.stdout,
                stderr=None if options.daemon else sys.stderr,
                signal_map={
                    signal.SIGTERM: self.terminate,
                    signal.SIGINT: self.interrupt,
                    }):
            logging.info('Starting emulator loop')
            self.dummy_logger = DummyLogger(port, bottles)
            # Loop around waiting for the dummy logger thread to terminate. If
            # we attempt to simply join() here then the thread blocks and the
            # signal handlers below never get a chance to execute
            try:
                while self.dummy_logger.is_alive():
                    self.dummy_logger.join(0.1)
            except (SystemExit, KeyboardInterrupt) as exc:
                pass
            logging.info('Waiting for emulator loop to finish')
            self.dummy_logger.join()
            logging.info('Exiting')

    def terminate(self, signum, frame):
        logging.info('Received SIGTERM')
        self.dummy_logger.terminated = True

    def interrupt(self, signum, frame):
        logging.info('Received SIGINT')
        self.dummy_logger.terminated = True


main = EmuApplication()

