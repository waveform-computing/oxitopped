# -*- coding: utf-8 -*-
# vim: set et sw=4 sts=4:

# Copyright 2012 Dave Hughes.
#
# This file is part of oxitopped.
#
# oxitopped is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# oxitopped is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# oxitopped.  If not, see <http://www.gnu.org/licenses/>.

"""
Main module for the oxitopemu utility.

"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import io
import os
import sys
import logging
import signal
from xml.etree.ElementTree import fromstring, tostring

import serial

from oxitopped.terminal import OxiTopApplication
from oxitopped.bottles import Bottle
from oxitopped.logger import DummyLogger
from oxitopped.daemon import DaemonContext


class EmuApplication(OxiTopApplication):
    """
    %prog [options] bottles-xml

    This utility emulates an OxiTop OC110 data dummy_logger for the purposes of
    easy development without access to an actual OC110. The bottle data served
    by the emulator is specified in an XML-based file which can be generated
    using oxitopdump or oxitopview with a real unit.
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
        if not args:
            # Use a default bottles definition file if none was specified
            args = [os.path.join(os.path.dirname(__file__), 'example.xml')]
        if len(args) == 1:
            with io.open(args[0], 'r') as bottles_file:
                bottles_xml = fromstring(bottles_file.read())
        else:
            self.parser.error(
                'You may only specify a single bottles definition file')
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
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.FileHandler):
                files_preserve.append(handler.stream)
        if not options.daemon:
            files_preserve.append(sys.stderr)
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

if __name__ == '__main__':
    sys.exit(main())
