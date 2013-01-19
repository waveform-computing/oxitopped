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

"""A simple application for listing data present on an OxiTop Data Logger

This application was developed after a quick reverse engineering of the basic
protocol of the OxiTop OC110 pressure data logger. Our understanding of the
protocol is incomplete at best but sufficient for data extraction.

"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import os
import logging

from oxitopdump import Application


class DumpApplication(Application):
    """
    %prog [options] [bottle-serial]... filename

    This utility dumps the sample readings stored on a connected OxiTop Data
    Logger to files in CSV or Excel format. If bottle-serial values are
    specified, the details of those bottles and all heads attached to them will
    be exported, otherwise a list of all available bottles is exported.
    The bottle-serial values may include *, ?, and [] wildcards. The filename
    value may include references to bottle attributes like {bottle.serial} or
    {bottle.id}.
    """

    def __init__(self):
        super(DumpApplication, self).__init__()
        self.parser.set_defaults(
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

    def main(self, options, args):
        super(DumpApplication, self).main(options, args)
        ext = os.path.splitext(args[-1])[-1].lower()
        try:
            if ext == '.csv':
                from oxitopdump.export_csv import CsvExporter
                exporter = CsvExporter()
            elif ext == '.xls':
                from oxitopdump.export_xls import ExcelExporter
                exporter = ExcelExporter()
            else:
                self.parser.error('unknown file extension %s' % ext)
        except ImportError:
            self.parser.error(
                'unable to load exporter for file extension %s' % ext)
        if len(args) > 1:
            try:
                options.points = int(options.points)
            except ValueError:
                self.parser.error(
                    '--moving-average value must be an integer number')
            if options.points % 2 == 0:
                self.parser.error(
                    '--moving-average value must be an odd number')
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
            for serial in serials:
                exporter.export_bottle(
                    args[-1], self.data_logger.bottle(serial),
                    delta=options.delta, points=options.points)
        else:
            exporter.export_bottles(args[0], self.data_logger.bottles)


main = DumpApplication()

