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

"""Defines the data structures representing the logger's sample data"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

from datetime import datetime, timedelta


ENCODING = 'ascii'
TIMESTAMP_FORMAT = '%y%m%d%H%M%S'


class Sample(object):
    """
    Represents a sample as collected from an OxiTop OC110 Data Logger.

    `sample` : the unique sample identifier
    `id` : additional user-assigned ID number (1-999), non-unique
    `start` : the timestamp at the start of the run
    `finish` : the timestamp at the end of the run
    `interval` : the interval between readings (expressed as a timedelta)
    `pressure` : the "pressure type" (what does this mean?)
    `bottle_volume` : the nominal volume (in ml) of the sample bottle
    `sample_volume` : the volume of the sample (in ml) within the bottle
    """

    def __init__(
            self, sample, id, start, finish, interval, pressure, bottle_volume,
            sample_volume, heads):
        self.sample = sample
        self.id = id
        self.start = start
        self.finish = finish
        self.interval = interval
        self.pressure = pressure
        self.bottle_volume = bottle_volume
        self.sample_volume = sample_volume
        self.heads = heads

    @classmethod
    def from_string(cls, data):
        data = data.decode(ENCODING).split('\r')
        # Discard the empty line at the end
        assert not data[-1]
        data = data[:-1]
        # Parse the first line for sample information
        (   _,             # ???
            _,             # ???
            _,             # ???
            id,            # I.D. No.
            sample,        # sample number
            start,         # start timestamp (YYMMDDhhmmss)
            finish,        # finish timestamp (YYMMDDhhmmss)
            _,             # ???
            _,             # ???
            _,             # ???
            _,             # ???
            measurements,  # number of measurements
            pressure,      # pressure type
            bottle_volume, # bottle volume (ml)
            sample_volume, # sample volume (ml)
            _,             # ???
            _,             # ???
            _,             # ???
            _,             # number of heads, perhaps???
            interval,      # interval of readings
        ) = data[0].split(',')
        return cls(
            sample,
            int(id),
            datetime.strptime(start, TIMESTAMP_FORMAT),
            datetime.strptime(finish, TIMESTAMP_FORMAT),
            # For some reason, intervals of 112 minutes are reported as 308?!
            timedelta(seconds=60 * int(112 if interval == 308 else interval)),
            int(pressure) // (24 * 60),
            float(bottle_volume),
            float(sample_volume),
            # Parse all subsequent lines as SampleHead objects
            [SampleHead.from_string(line) for line in data[1:]]
            )

    def __str__(self):
        return (','.join((
            '0',
            '0',
            '3',
            str(self.id),
            str(self.sample),
            self.start.strftime(TIMESTAMP_FORMAT),
            self.finish.strftime(TIMESTAMP_FORMAT),
            '2',
            '5',
            '240',
            '40',
            str(self.measurements),
            str(self.pressure * 24 * 60),
            '%.0f' % self.bottle_volume,
            '%.1f' % self.sample_volume,
            '0',
            str({
                28: 10,
                14: 10,
                3:  6,
                2:  4,
                1:  2,
                }[self.pressure]),
            '2',
            '1',
            str(308 if (interval.seconds // 60) == 112 else (interval.seconds // 60)),
            )) +
            '\r' +
            ''.join(str(head) for head in self.heads)).encode(ENCODING)

    def __unicode__(self):
        return str(self).decode(ENCODING)


class SampleHead(object):
    """
    Represents a single head on a gas bottle.

    `serial` : the serial number of the head
    """

    def __init__(self, serial):
        self.serial = serial
        self.readings = []

    @classmethod
    def from_string(cls, data):
        data = data.decode(ENCODING)
        (   _,      # blank value (due to extraneous leading comma)
            serial, # serial number of head
            _,      # ???
            _,      # blank value (due to extraneous trailing comma)
        ) = data.split(',')
        return cls(serial)

    def __str__(self):
        return (','.join((
            '',
            self.serial,
            '150',
            '',
            )) + '\r').encode(ENCODING)

    def __unicode__(self):
        return str(self).decode(ENCODING)

