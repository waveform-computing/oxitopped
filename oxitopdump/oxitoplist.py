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
import fnmatch
import logging

from oxitopdump import Application


class ListApplication(Application):
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
            )
        self.parser.add_option(
            '-r', '--readings', dest='readings', action='store_true',
            help='if specified, output readings for each head after '
            'displaying bottle details')
        self.parser.add_option(
            '-a', '--absolute', dest='delta', action='store_false',
            help='if specified with --readings, output absolute pressure '
            'values instead of deltas against the first value')

    def main(self, options, args):
        super(ListApplication, self).main(options, args)
        if args:
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
                    serial, readings=options.readings, delta=options.delta)
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

    def print_bottle(self, serial, readings=False, delta=True):
        bottle = self.data_logger.bottle(serial)
        max_readings = max(len(head.readings) for head in bottle.heads)
        form = [
            ('Serial',               bottle.serial),
            ('ID',                   str(bottle.id)),
            ('Started',              bottle.start.strftime('%Y-%m-%d %H:%M:%S')),
            ('Finished',             bottle.start.strftime('%Y-%m-%d %H:%M:%S')),
            ('Readings Interval',    str(bottle.interval)),
            ('Completed',            bottle.completed),
            ('Mode',                 bottle.mode_string),
            ('Bottle Volume',        '%.1fml' % bottle.bottle_volume),
            ('Sample Volume',        '%.1fml' % bottle.sample_volume),
            ('Dilution',             '1+%d' % bottle.dilution),
            ('Desired no. of Values', str(bottle.measurements)),
            ('Actual no. of Values',  str(max_readings)),
            ('Heads',                 str(len(bottle.heads))),
            ]
        self.print_form(form)
        if readings:
            print()
            table = [
                tuple('Head' for head in bottle.heads),
                tuple(head.serial for head in bottle.heads),
                ]
            table.extend(
                tuple(
                    str(head.readings[reading] - (head.readings[0] if delta else 0))
                    if reading < len(head.readings) else ''
                    for head in bottle.heads
                    )
                for reading in range(max_readings)
                )
            self.print_table(table, header_lines=2)


main = ListApplication()

