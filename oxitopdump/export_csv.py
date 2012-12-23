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

"""Module implementing CSV exporters for bottles and bottle readings."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import io
import csv
from itertools import izip_longest

from oxitopdump.bottles import DataAnalyzer


class CsvExporter(Exporter):
    def __init__(self):
        super(CsvExporter).__init__()
        self.delimiter = ','
        self.lineterminator = '\r\n'
        self.quotechar = '"'
        self.quoting = csv.QUOTE_MINIMAL
        self.header_row = True
        self.timestamp_format = '%Y-%m-%d %H:%M:%S'

    def export_bottles(self, filename, bottles):
        with io.open(filename, 'wb') as output_file:
            writer = csv.writer(output_file,
                delimiter=self.delimiter,
                lineterminator=self.lineterminator,
                quotechar=self.quotechar,
                quoting=self.quoting,
                doublequote=csv.excel.doublequote)
            if self.header_row:
                writer.writerow((
                    'Serial',
                    'ID',
                    'Start',
                    'Finish',
                    'Mode',
                    'Bottle Vol',
                    'Sample Vol',
                    'Dilution',
                    'Heads',
                    ))
            for bottle in bottles:
                row = (
                    bottle.serial,
                    bottle.id,
                    bottle.start.strftime(self.timestamp_format),
                    bottle.finish.strftime(self.timestamp_format),
                    bottle.mode_string,
                    bottle.bottle_volume,
                    bottle.sample_volume,
                    bottle.dilution,
                    len(bottle.heads),
                    )
                writer.writerow(row)

    def export_bottle(self, filename, bottle, delta=True, points=1):
        analyzer = DataAnalyzer(bottle, delta=delta, points=points)
        with io.open(filename, 'wb') as output_file:
            writer = csv.writer(output_file,
                delimiter=self.delimiter,
                lineterminator=self.lineterminator,
                quotechar=self.quotechar,
                quoting=self.quoting,
                doublequote=csv.excel.doublequote)
            if self.header_row:
                writer.writerow([
                    'No.',
                    'Timestamp',
                    'Offset',
                    ] + [
                    'Head %s' % head.serial
                    for head in analyzer.bottle.heads
                    ])
            for row in izip_longest(
                    range(len(analyzer.timestamps)),
                    analyzer.timestamps,
                    (str(t - analyzer.bottle.start) for t in analyzer.timestamps),
                    *analyzer.heads):
                writer.writerow(row)
