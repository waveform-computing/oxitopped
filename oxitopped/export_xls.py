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

"""Module implementing Excel exporters for bottles and bottle readings."""

from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

from datetime import datetime
from itertools import izip_longest

import xlwt

from oxitopped.bottles import DataAnalyzer


class ExcelExporter(object):
    def __init__(self):
        super(ExcelExporter, self).__init__()
        self.header_row = True
        self.row_colors = True

    def export_bottles(self, filename_or_obj, bottles):
        header_style = xlwt.easyxf('font: bold on')
        even_default_style = xlwt.easyxf('')
        even_text_style = xlwt.easyxf(num_format_str='@')
        even_date_style = xlwt.easyxf(num_format_str='ddd d mmm yyyy hh:mm:ss')
        odd_default_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue')
        odd_text_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue', num_format_str='@')
        odd_date_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue', num_format_str='ddd d mmm yyyy hh:mm:ss')
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('OC110')
        row = 0
        if self.header_row:
            for col, heading in enumerate((
                'Serial',
                'ID',
                'Start',
                'Finish',
                'Mode',
                'Bottle Vol',
                'Sample Vol',
                'Dilution',
                'Heads',
                )):
                worksheet.write(row, col, heading, header_style)
            row += 1
            # Freeze the header row at the top of the sheet
            worksheet.panes_frozen = True
            worksheet.horz_split_pos = 1
        for bottle in bottles:
            if self.row_colors:
                (default_style, text_style, date_style) = [
                    (even_default_style, even_text_style, even_date_style),
                    (odd_default_style, odd_text_style, odd_date_style)
                    ][row % 2]
            else:
                (default_style, text_style, date_style) = (
                    even_default_style, even_text_style, even_date_style
                    )
            data = (
                bottle.serial,
                bottle.id,
                bottle.start,
                bottle.finish,
                bottle.mode_string,
                bottle.bottle_volume,
                bottle.sample_volume,
                bottle.dilution,
                len(bottle.heads),
                )
            for col, value in enumerate(data):
                if isinstance(value, datetime):
                    worksheet.write(row, col, value, date_style)
                elif isinstance(value, basestring):
                    worksheet.write(row, col, value, text_style)
                else:
                    worksheet.write(row, col, value, default_style)
            row += 1
        worksheet.col(1).width = 4 * 256
        worksheet.col(2).width = 24 * 256
        worksheet.col(3).width = 24 * 256
        workbook.save(filename_or_obj)

    def export_bottle(self, filename_or_obj, bottle, delta=True, points=1):
        analyzer = DataAnalyzer(bottle, delta=delta, points=points)
        header_style = xlwt.easyxf('font: bold on')
        even_default_style = xlwt.easyxf('')
        even_text_style = xlwt.easyxf(num_format_str='@')
        even_date_style = xlwt.easyxf(num_format_str='ddd d mmm yyyy hh:mm:ss')
        odd_default_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue')
        odd_text_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue', num_format_str='@')
        odd_date_style = xlwt.easyxf('pattern: pattern solid, fore_color ice_blue', num_format_str='ddd d mmm yyyy hh:mm:ss')
        workbook = xlwt.Workbook()
        # Create the bottle details sheet
        worksheet = workbook.add_sheet('Bottle %s' % analyzer.bottle.serial)
        data = (
            ('Bottle Serial',         analyzer.bottle.serial),
            ('Bottle ID',             analyzer.bottle.id),
            ('Bottle Volume',         analyzer.bottle.bottle_volume),
            ('Sample Volume',         analyzer.bottle.sample_volume),
            ('Dilution',              '1+%d' % analyzer.bottle.dilution),
            ('Measurement Mode',      analyzer.bottle.mode_string),
            ('Measurement Complete',  analyzer.bottle.finish < datetime.now()),
            ('Start Timestamp',       analyzer.bottle.start),
            ('Finish Timestamp',      analyzer.bottle.finish),
            ('Desired no. of Values', analyzer.bottle.expected_measurements),
            ('Actual no. of Values',  analyzer.bottle.actual_measurements),
            )
        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                if col == 0:
                    worksheet.write(row, col, value, header_style)
                elif isinstance(value, datetime):
                    worksheet.write(row, col, value, even_date_style)
                elif isinstance(value, basestring):
                    worksheet.write(row, col, value, even_text_style)
                else:
                    worksheet.write(row, col, value, even_default_style)
        worksheet.col(0).width = 22 * 256
        worksheet.col(1).width = 24 * 256
        # Create the bottle readings sheet
        worksheet = workbook.add_sheet('Readings')
        row = 0
        if self.header_row:
            data = [
                'No.',
                'Timestamp',
                'Offset',
                ] + [
                'Head %s' % head.serial
                for head in analyzer.bottle.heads
                ]
            for col, value in enumerate(data):
                worksheet.write(row, col, value, header_style)
            row += 1
            # Freeze the header row at the top of the sheet
            worksheet.panes_frozen = True
            worksheet.horz_split_pos = 1
        for data in izip_longest(
                range(len(analyzer.timestamps)),
                analyzer.timestamps,
                (str(t - analyzer.bottle.start) for t in analyzer.timestamps),
                *analyzer.heads):
            if self.row_colors:
                (default_style, text_style, date_style) = [
                    (even_default_style, even_text_style, even_date_style),
                    (odd_default_style, odd_text_style, odd_date_style)
                    ][data[0] % 2]
            else:
                (default_style, text_style, date_style) = (
                    even_default_style, even_text_style, even_date_style
                    )
            for col, value in enumerate(data):
                if isinstance(value, datetime):
                    worksheet.write(row, col, value, date_style)
                elif isinstance(value, basestring):
                    worksheet.write(row, col, value, text_style)
                else:
                    worksheet.write(row, col, value, default_style)
            row += 1
        worksheet.col(0).width = 4 * 256
        worksheet.col(1).width = 24 * 256
        worksheet.col(2).width = 24 * 256
        workbook.save(filename_or_obj)

