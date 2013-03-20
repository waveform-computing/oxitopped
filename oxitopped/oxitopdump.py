#!/usr/bin/env python
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
Main module for the oxitopdump utility.
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import os
import sys
import csv
import fnmatch
from datetime import datetime

from oxitopped.terminal import OxiTopApplication


TERMINATORS = {
    'dos':  b'\r\n',
    'unix': b'\n',
    'mac':  b'\r',
    }

QUOTING = {
    'all':        csv.QUOTE_ALL,
    'none':       csv.QUOTE_NONE,
    'minimal':    csv.QUOTE_MINIMAL,
    'nonnumeric': csv.QUOTE_NONNUMERIC,
    }

class DumpApplication(OxiTopApplication):
    """
    %prog [options] [bottle-serial]... filename

    This utility dumps the sample readings stored on a connected OxiTop Data
    Logger to files in CSV or Excel format. If bottle-serial values are
    specified, the details of those bottles and all heads attached to them will
    be exported, otherwise a list of all available bottles is exported.
    The bottle-serial values may include *, ?, and [] wildcards. The filename
    value may include references to bottle attributes like {bottle.serial} or
    {bottle.id} (and must if the bottle-serial expansion results in more than
    one bottle's readings being retrieved).
    """

    def __init__(self):
        super(DumpApplication, self).__init__()
        self.parser.set_defaults(
            delimiter=',',
            lineterminator='dos',
            quotechar='"',
            quoting='minimal',
            timestamp_format='%Y-%m-%d %H:%M:%S',
            header_row=False,
            row_colors=False,
            delta=True,
            points=1,
            )
        self.parser.add_option(
            '-a', '--absolute', dest='delta', action='store_false',
            help='if specified, export absolute pressure values instead of '
            'deltas against the first value')
        self.parser.add_option(
            '-m', '--moving-average', dest='points', action='store',
            help='if specified, export a moving average over the specified '
            'number of points instead of actual readings')
        self.parser.add_option(
            '-H', '--header', dest='header_row', action='store_true',
            help='if specified, a header row will be written in the '
            'output file')
        self.parser.add_option(
            '-R', '--row-colors', dest='row_colors', action='store_true',
            help='if specified, alternate row coloring will be used in the '
            'output file (.xls only)')
        self.parser.add_option(
            '-C', '--column-delimiter', dest='delimiter', action='store',
            help='specifies the column delimiter in the output file. Defaults '
            'to "%default" (.csv only)')
        self.parser.add_option(
            '-L', '--line-terminator', dest='lineterminator', action='store',
            help='specifies the line terminator in the output file. Defaults '
            'to "%default" (.csv only)')
        self.parser.add_option(
            '-Q', '--quote-char', dest='quotechar', action='store',
            help='specifies the character used for quoting strings in the '
            'output file. Defaults to %default (.csv only)')
        self.parser.add_option(
            '-U', '--quoting', dest='quoting', action='store',
            help='specifies the quoting behaviour used in the output file. '
            'Defaults to %default (.csv only). Can be none, all, minimal, or '
            'nonnumeric')
        self.parser.add_option(
            '-T', '--timestamp-format', dest='timestamp_format', action='store',
            help='specifies the formatting of timestamps in the output file. '
            'Defaults to %default (.csv only)')

    def main(self, options, args):
        super(DumpApplication, self).main(options, args)
        if len(args) < 1:
            self.parser.error('you must specify an output filename')
        try:
            options.points = int(options.points)
        except ValueError:
            self.parser.error(
                '--moving-average value must be an integer number')
        if options.points % 2 == 0:
            self.parser.error(
                '--moving-average value must be an odd number')
        ext = os.path.splitext(args[-1])[-1].lower()
        try:
            if ext == '.csv':
                from oxitopped.export_csv import CsvExporter
                exporter = CsvExporter()
                exporter.delimiter = str(options.delimiter)
                exporter.quotechar = str(options.quotechar)
                try:
                    exporter.lineterminator = TERMINATORS[options.lineterminator]
                except KeyError:
                    self.parser.error(
                        '--line-terminator must be one of %s' % (
                            ', '.join(TERMINATORS.keys())))
                try:
                    exporter.quoting = QUOTING[options.quoting]
                except KeyError:
                    self.parser.error(
                        '--quoting must be one of %s' % (
                            ', '.join(QUOTING.keys())))
                try:
                    datetime.now().strftime(options.timestamp_format)
                except ValueError as exc:
                    self.parser.error(
                        'invalid value for --timestamp-format: %s' % str(exc))
                else:
                    exporter.timestamp_format = options.timestamp_format
            elif ext == '.xls':
                from oxitopped.export_xls import ExcelExporter
                exporter = ExcelExporter()
            else:
                self.parser.error('unknown file extension %s' % ext)
            exporter.header_row = options.header_row
        except ImportError:
            self.parser.error(
                'unable to load exporter for file extension %s' % ext)
        filename_or_obj = sys.stdout if args[-1] == '-' else args[-1]
        args = args[:-1]
        if len(args) > 0:
            # Construct a set of unique serial numbers (we use a set instead
            # of a list so that in the event of multiple patterns matching a
            # single bottle it doesn't get listed multiple times)
            serials = set()
            for arg in args:
                if set('*?[') & set(arg):
                    serials |= set(
                        fnmatch.filter((
                            bottle.serial
                            for bottle in self.data_logger.bottles), arg))
                else:
                    serials.add(arg)
            if len(serials) > 1:
                # Ensure output filename is a string with a format part
                if hasattr(filename_or_obj, 'write'):
                    self.parser.error(
                        'cannot use stdout for output with more than '
                        'one bottle')
                bottles = [
                    self.data_logger.bottle(serial)
                    for serial in serials
                    ]
                bottles = [
                    (bottle, filename_or_obj.format(bottle=bottle))
                    for bottle in bottles
                    ]
                all_filenames = [f for (_, f) in bottles]
                if len(set(all_filenames)) < len(bottles):
                    self.parser.error(
                        'filename must be unique for each bottle '
                        '(use {bottle.serial} in filename)')
                for bottle, filename in bottles:
                    exporter.export_bottle(
                        filename, bottle,
                        delta=options.delta, points=options.points)
            else:
                bottle = self.data_logger.bottle(serials.pop())
                if not hasattr(filename_or_obj, 'write'):
                    filename_or_obj = filename_or_obj.format(bottle=bottle)
                exporter.export_bottle(
                    filename_or_obj, bottle,
                    delta=options.delta, points=options.points)
        else:
            exporter.export_bottles(filename_or_obj, self.data_logger.bottles)


main = DumpApplication()

if __name__ == '__main__':
    sys.exit(main())
