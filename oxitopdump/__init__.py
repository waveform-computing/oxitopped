#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set et sw=4 sts=4:

# Copyright 2012 Dave Hughes.
#
# This file is part of oxitopget.
#
# oxitopget is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# oxitopget is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# oxitopget.  If not, see <http://www.gnu.org/licenses/>.

"""A simple application for grabbing data from an OxiTop OC110 Data Logger

This application was developed after a quick reverse engineering of the basic
protocol of the OxiTop OC110 pressure data logger. Our understanding of the
protocol is incomplete at best but sufficient for data extraction. The actual
steps of the protocol are as follows:

 1. Client sends <CR> (ASCII code 13) which starts the conversation
 2. OC110 sends "LOGON>" (without the quotes)
 3. Client sends "MAID" <CR> (manufacturer ID maybe? <CR> again means ASCII 13)
 4. OC110 sends "OC110" <CR> ">"
 5. Client sends "GAPB" <CR> (get all ... erm?)
 6. OC110 begins transmitting all data
 7. OC110 terminates with ">" prompt

"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import sys
import os
import csv
import serial
import optparse
import textwrap
import logging
import traceback
import locale

__version__ = '0.1'

# Use the user's default locale instead of C
locale.setlocale(locale.LC_ALL, '')


class HelpFormatter(optparse.IndentedHelpFormatter):
    # Customize the width of help output
    def __init__(self):
        width = 75
        optparse.IndentedHelpFormatter.__init__(
                self, max_help_position=width // 3, width=width)


class OptionParser(optparse.OptionParser):
    # Customize error handling to raise an exception (default simply prints an
    # error and terminates execution)
    def error(self, msg):
        raise optparse.OptParseError(msg)


class Application(object):
    """%prog [options] filename

    This utility extracts data from an OxiTop C110 pressure data logger.
    Various options are provided to specify the serial port that the data
    logger is connected to. The data will be written to the specified filename
    in CSV format.
    """

    def __init__(self):
        super(Application, self).__init__()
        self.port = None
        self.wrapper = textwrap.TextWrapper()
        self.wrapper.width = 75
        self.parser = OptionParser(
            usage=self.__doc__.split('\n')[0],
            version=__version__,
            description=self.wrapper.fill('\n'.join(
                line.lstrip()
                for line in self.__doc__.split('\n')[1:]
                if line.lstrip()
            )),
            formatter=HelpFormatter())
        self.parser.set_defaults(
            debug=False,
            logfile='',
            loglevel=logging.WARNING,
            port='/dev/ttyUSB0',
            )
        self.parser.add_option(
            '-q', '--quiet', dest='loglevel', action='store_const',
            const=logging.ERROR, help='produce less console output')
        self.parser.add_option(
            '-v', '--verbose', dest='loglevel', action='store_const',
            const=logging.INFO, help='produce more console output')
        self.parser.add_option(
            '-l', '--log-file', dest='logfile',
            help='log messages to the specified file')
        self.parser.add_option(
            '-D', '--debug', dest='debug', action='store_true',
            help='enables debug mode (runs under PDB)')
        self.parser.add_option(
            '-p', '--port', dest='port', action='store',
            help='specify the port which the OxiTop is connected to. This '
            'will be something like /dev/ttyUSB0 on Linux and something like '
            'COM1 on Windows')

    def __call__(self, args=None):
        if args is None:
            args = sys.argv[1:]
        (options, args) = self.parser.parse_args(list(args))
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter('%(message)s'))
        console.setLevel(options.loglevel)
        logging.getLogger().addHandler(console)
        if options.logfile:
            logfile = logging.FileHandler(options.logfile)
            logfile.setFormatter(logging.Formatter('%(asctime)s, %(levelname)s, %(message)s'))
            logfile.setLevel(logging.DEBUG)
            logging.getLogger().addHandler(logfile)
        if options.debug:
            console.setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
        if options.debug:
            import pdb
            return pdb.runcall(self.main, options, args)
        else:
            try:
                return self.main(options, args) or 0
            except:
                return self.handle(*sys.exc_info())

    def handle(self, type, value, tb):
        """Exception hook for non-debug mode."""
        if issubclass(type, (SystemExit, KeyboardInterrupt)):
            # Just ignore system exit and keyboard interrupt errors (after all,
            # they're user generated)
            return 130
        elif issubclass(type, (IOError, serial.SerialException)):
            # For simple errors like IOError and SerialException just output
            # the message which should be sufficient for the end user (no need
            # to confuse them with a full stack trace)
            logging.critical(str(value))
            return 1
        elif issubclass(type, (optparse.OptParseError,)):
            # For option parser errors output the error along with a message
            # indicating how the help page can be displayed
            logging.critical(str(value))
            logging.critical('Try the --help option for more information.')
            return 2
        else:
            # Otherwise, log the stack trace and the exception into the log
            # file for debugging purposes
            for line in traceback.format_exception(type, value, tb):
                for s in line.rstrip().split('\n'):
                    logging.critical(s)
            return 1

    def main(self, options, args):
        self.port = serial.Serial(
            options.port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=5,
            rtscts=True)
        self.send('\r')
        self.expect(['LOGON', 'INVALID COMMAND'])
        self.send('MAID\r')
        self.expect(['OC110'])
        self.send('GAPB\r')
        logging.info('Entering data retrieval loop')
        rows = []
        buf = ''
        while True:
            data = self.port.read().decode('ASCII')
            if not data:
                raise ValueError('Failed to read any data before timeout')
            buf += data
            if buf == '>':
                logging.info('Received prompt, terminating data retrieval loop')
                break
            if '\r' in buf:
                rows.append(buf)
                logging.info('Received data line %d' % len(rows))
                buf = ''
        for rownum, row in enumerate(rows):
            print(rownum, row)

    def expect(self, patterns):
        logging.info('Waiting for response')
        response = ''
        while '>' not in response:
            data = self.port.read().decode('ASCII')
            if not data:
                raise ValueError('Failed to read any data before timeout')
            response += data
        # Strip off the prompt
        response = response.rstrip('>')
        # Split the responsefer on the CRs
        response = response.split('\r')
        # Remove any blank lines
        response = [line for line in response if line]
        # Check we only received a single non-blank response
        if len(response) > 1:
            raise ValueError('Recevied more than one line in response')
        response = response[0]
        if response not in patterns:
            raise ValueError(
                'Expected "%r" but received %s' % (patterns[0], repr(response)))
        logging.info('Received response %s' % repr(response))
        return response

    def send(self, data):
        logging.info('Sending command %s' % repr(data))
        written = self.port.write(data)
        if written != len(data):
            raise ValueError(
                'Only wrote first %d bytes of %s' % (written, repr(data)))


main = Application()
