#!/usr/bin/env python
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

"""The base class for command line oxitop applications"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import sys
import os
import optparse
import textwrap
import logging
import traceback
import locale

import serial

import oxitopdump.patches
from oxitopdump.logger import DataLogger, DummyLogger
from oxitopdump.nullmodem import null_modem


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
    """
    Base class for command line applications.

    In descendent classes, the documentation for the --help parameter should
    be placed in the class' __doc__ field, where this text is.
    """

    def __init__(self):
        super(Application, self).__init__()
        self.console = None
        self.logfile = None
        self.dummy_logger = None
        self.data_logger = None
        self.progress_visible = False
        self.wrapper = textwrap.TextWrapper()
        self.wrapper.width = 75
        self.parser = OptionParser(
            usage=self.__doc__.strip().split('\n')[0],
            version=__version__,
            description=self.wrapper.fill('\n'.join(
                line.lstrip()
                for line in self.__doc__.strip().split('\n')[1:]
                if line.lstrip()
            )),
            formatter=HelpFormatter())
        self.parser.set_defaults(
            debug=False,
            logfile='',
            loglevel=logging.WARNING,
            port='COM1' if sys.platform.startswith('win') else '/dev/ttyUSB0',
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
            help='specify the port which the OxiTop Data Logger is connected '
            'to. This will be something like /dev/ttyUSB0 on Linux or COM1 '
            'on Windows')

    def __call__(self, args=None):
        if args is None:
            args = sys.argv[1:]
        (options, args) = self.parser.parse_args(list(args))
        self.progress_visible = (options.loglevel == logging.INFO)
        self.console = logging.StreamHandler(sys.stderr)
        self.console.setFormatter(logging.Formatter('%(message)s'))
        self.console.setLevel(options.loglevel)
        logging.getLogger().addHandler(self.console)
        if options.logfile:
            self.logfile = logging.FileHandler(options.logfile)
            self.logfile.setFormatter(logging.Formatter('%(asctime)s, %(levelname)s, %(message)s'))
            self.logfile.setLevel(logging.DEBUG)
            logging.getLogger().addHandler(self.logfile)
        if options.debug:
            console.setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger().setLevel(logging.INFO)
        try:
            if options.debug:
                import pdb
                return pdb.runcall(self.main, options, args)
            else:
                try:
                    return self.main(options, args) or 0
                except:
                    return self.handle(*sys.exc_info())
        finally:
            if self.dummy_logger:
                self.dummy_logger.terminated = True
            # The port close call here isn't strictly necessary, but allows us
            # to terminate a blocking read in the DummyLogger class early which
            # in turn greatly speeds up testing
            if self.data_logger:
                self.data_logger.port.close()

    def handle(self, type, value, tb):
        """
        Exception hook for non-debug mode.
        """
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

    def print_table(self, lines, header_lines=1, footer_lines=0):
        """
        Routine for pretty-printing a text table.

        `lines` : a sequence of tuples representing a row of values in the table
        `header_lines` : number of lines at the start that are headers
        `footer_lines` : number of lines at the end that are footers
        """
        lines = list(lines)
        # Calculate the maximum length of each field
        columns = max(len(line) for line in lines)
        lengths = [
            max(len(line[column])
                if column < len(line) else 0 for line in lines)
            for column in range(columns)
            ]
        # Insert separators
        if header_lines != 0:
            lines.insert(header_lines, tuple('-' * l for l in lengths))
        if footer_lines != 0:
            lines.insert(-footer_lines, tuple('-' * l for l in lengths))
        # Output the data
        for line in lines:
            print(' '.join('%-*s' % (l, s) for (l, s) in zip(lengths, line)))

    def print_form(self, lines, fmt='{field: <{width}}{value}'):
        """
        Routine for pretty-printing a form of fields.

        `lines` : a sequence of 2-tuples representing each field and its value
        `fmt` : a format string specifying how to lay out each line
        """
        lines = list(lines)
        columns = max(len(line) for line in lines)
        assert columns == 2
        # Calculate the maximum length of each field
        width = max(len(line[0]) for line in lines) + 2
        for (field, value) in lines:
            print(fmt.format(width=width, field=field, value=value))

    progress_spinner = ['\\', '|', '/' ,'-']

    def progress_start(self):
        self.progress_index = 0
        self.progress_update(erase=False)

    def progress_update(self, erase=True):
        if not self.progress_visible:
            return
        if erase:
            sys.stderr.write('\b')
        sys.stderr.write(self.progress_spinner[self.progress_index % len(self.progress_spinner)])
        sys.stderr.flush()
        self.progress_index += 1

    def progress_finish(self):
        if not self.progress_visible:
            return
        sys.stderr.write('\b')

    def main(self, options, args):
        if options.port == 'TEST':
            data_logger_port, dummy_logger_port = null_modem(
                baudrate=9600, bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                timeout=5, rtscts=True)
            self.dummy_logger = DummyLogger(dummy_logger_port)
        else:
            data_logger_port = serial.Serial(
                options.port, baudrate=9600, bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                timeout=5, rtscts=True)
        self.data_logger = DataLogger(data_logger_port, progress=(
            self.progress_start,
            self.progress_update,
            self.progress_finish,
            ))

