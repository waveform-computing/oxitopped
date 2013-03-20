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
Main module for the oxitoplist utility.
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import sys
import fnmatch
from itertools import izip_longest

from oxitopped.terminal import OxiTopApplication
from oxitopped.bottles import DataAnalyzer


class ListApplication(OxiTopApplication):
    """
    %prog [options] [bottle-serial]...

    This utility lists the sample results stored on a connected OxiTop Data
    Logger. If bottle-serial values are specified, the details of those bottles
    and all heads attached to them will be displayed, otherwise a list of all
    available bottle serials provided. The bottle-serial values may include *,
    ?, and [] wildcards.
    """

    def __init__(self):
        super(ListApplication, self).__init__()
        self.parser.set_defaults(
            readings=False,
            delta=True,
            points=1,
            )
        self.parser.add_option(
            '-r', '--readings', dest='readings', action='store_true',
            help='if specified, output readings for each head after '
            'displaying bottle details')
        self.parser.add_option(
            '-a', '--absolute', dest='delta', action='store_false',
            help='if specified with --readings, output absolute pressure '
            'values instead of deltas against the first value')
        self.parser.add_option(
            '-m', '--moving-average', dest='points', action='store',
            help='if specified with --readings, output a moving average '
            'over the specified number of points instead of actual readings')

    def main(self, options, args):
        super(ListApplication, self).main(options, args)
        if args:
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
            first = True
            for serial in serials:
                if first:
                    first = False
                else:
                    print()
                self.print_bottle(
                    serial, readings=options.readings, delta=options.delta,
                    points=options.points)
        else:
            self.print_bottles()

    def print_bottles(self):
        table = [
            ('Serial', 'ID', 'Started', 'Finished', 'Complete', 'Mode', 'Heads'),
            ]
        for bottle in self.data_logger.bottles:
            table.append((
                bottle.serial,
                str(bottle.id),
                bottle.start.strftime('%Y-%m-%d'),
                bottle.finish.strftime('%Y-%m-%d'),
                bottle.completed,
                bottle.mode_string,
                str(len(bottle.heads)),
                ))
        self.print_table(table)
        print()
        print('%d results returned' % len(self.data_logger.bottles))

    def print_bottle(self, serial, readings=False, delta=True, points=1):
        bottle = self.data_logger.bottle(serial)
        form = [
            ('Serial',               bottle.serial),
            ('ID',                   str(bottle.id)),
            ('Started',              bottle.start.strftime('%a, %d %b %Y, %H:%M:%S')),
            ('Finished',             bottle.finish.strftime('%a, %d %b %Y, %H:%M:%S')),
            ('Readings Interval',    str(bottle.interval)),
            ('Completed',            bottle.completed),
            ('Mode',                 bottle.mode_string),
            ('Bottle Volume',        '%.1fml' % bottle.bottle_volume),
            ('Sample Volume',        '%.1fml' % bottle.sample_volume),
            ('Dilution',             '1+%d' % bottle.dilution),
            ('Desired no. of Values', str(bottle.expected_measurements)),
            ('Actual no. of Values',  str(bottle.actual_measurements)),
            ('Heads',                 str(len(bottle.heads))),
            ]
        self.print_form(form)
        if readings:
            analyzer = DataAnalyzer(bottle, delta=delta, points=points)
            print()
            table = [
                tuple([''] + ['Head' for head in bottle.heads]),
                tuple(['Timestamp'] + [head.serial for head in bottle.heads]),
                ]
            table.extend(
                tuple(
                    str(reading)
                    for reading in head
                    )
                for head in izip_longest(analyzer.timestamps, *analyzer.heads)
                )
            self.print_table(table, header_lines=2)


main = ListApplication()

if __name__ == '__main__':
    sys.exit(main())
