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

"""
Defines the structures and interfaces for gathering data from an OC110

This module defines a couple of data structures which represent gas bottle
(`Bottle`) and the measuring head(s) of a gas bottle (`BottleHead`). These can
be constructed manually but more usually will be obtained from an instance of
`DataLogger` which provides an interface to the OC110 serial port. For testing
purposes a "fake OC110" can be found in the `DummySerial` class which takes the
same initialization parameters as the Python `Serial` class and hence can be
used in place of it.
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import logging
from datetime import datetime, timedelta
from collections import deque
from itertools import islice

import serial


ENCODING = 'ascii'
TIMESTAMP_FORMAT = '%y%m%d%H%M%S'


class Bottle(object):
    """
    Represents a bottle as collected from an OxiTop OC110 Data Logger.

    `serial` : the bottle serial number
    `id` : additional user-assigned ID number (1-999), non-unique
    `start` : the timestamp at the start of the run
    `finish` : the timestamp at the end of the run
    `interval` : the interval between readings (expressed as a timedelta)
    `measurements` : the expected number of measurements
    `mode` : one of 'pressure' or 'bod'
    `bottle_volume` : the nominal volume (in ml) of the bottle
    `sample_volume` : the volume of the sample (in ml) within the bottle
    `logger` : a DataLogger instance that can be used to update the bottle
    """

    def __init__(
            self, serial, id, start, finish, interval, expected_measurements,
            mode, bottle_volume, sample_volume, dilution, logger=None):
        self.logger = logger
        try:
            date, num = serial.split('-', 1)
            datetime.strptime(date, '%y%m%d')
            assert 1 <= int(num) <= 99
        except (ValueError, AssertionError) as exc:
            raise ValueError('invalid serial number %s' % serial)
        if not (1 <= id <= 999):
            raise ValueError('id must be an integer between 1 and 999')
        if not mode in ('pressure', 'bod'):
            raise ValueError('mode must be one of "pressure" or "bod"')
        self.serial = serial
        self.id = id
        self.start = start
        self.finish = finish
        self.interval = interval
        self.expected_measurements = expected_measurements
        self.mode = mode
        self.bottle_volume = float(bottle_volume)
        self.sample_volume = float(sample_volume)
        self.dilution = dilution
        self.heads = []

    @property
    def actual_measurements(self):
        return max(len(head.readings) for head in self.heads)

    @property
    def mode_string(self):
        return (
            'Pressure %dd' % (self.finish - self.start).days
                if self.mode == 'pressure' else
            'BOD'
                if self.mode == 'bod' else
            'Unknown'
            )

    @property
    def completed(self):
        return 'Yes' if self.finish < datetime.now() else 'No'

    @classmethod
    def from_string(cls, data, logger=None):
        data = data.decode(ENCODING).split('\r')
        # Discard the empty line at the end
        assert not data[-1]
        data = data[:-1]
        # Parse the first line for bottle information
        (   _,             # ???
            _,             # ???
            _,             # ???
            id,            # I.D. No.
            serial,        # bottle serial number
            start,         # start timestamp (YYMMDDhhmmss)
            finish,        # finish timestamp (YYMMDDhhmmss)
            _,             # ???
            _,             # ???
            _,             # ???
            _,             # ???
            measurements,  # number of measurements
            pressure,      # pressure type?
            bottle_volume, # bottle volume (ml)
            sample_volume, # sample volume (ml)
            _,             # ???
            _,             # ???
            _,             # ???
            _,             # number of heads, perhaps???
            interval,      # interval of readings (perhaps, see 308<=>112 note below)
        ) = data[0].split(',')
        bottle = cls(
            '%s-%s' % (serial[:-2], serial[-2:]),
            int(id),
            datetime.strptime(start, TIMESTAMP_FORMAT),
            datetime.strptime(finish, TIMESTAMP_FORMAT),
            # XXX For some reason, intervals of 112 minutes are reported as 308?!
            timedelta(seconds=60 * int(112 if int(interval) == 308 else interval)),
            int(measurements),
            'pressure',
            float(bottle_volume),
            float(sample_volume),
            0,
            # Parse all subsequent lines as BottleHead objects
            logger
            )
        bottle.heads = [
            BottleHead.from_string(bottle, line)
            for line in data[1:]
            ]
        return bottle

    def __str__(self):
        return (','.join((
            '0',
            '0',
            '3',
            str(self.id),
            ''.join(self.serial.split('-', 1)),
            self.start.strftime(TIMESTAMP_FORMAT),
            self.finish.strftime(TIMESTAMP_FORMAT),
            '2',
            '5',
            '240',
            '40',
            str(self.expected_measurements),
            str((self.finish - self.start).days * 24 * 60),
            '%.0f' % self.bottle_volume,
            '%.1f' % self.sample_volume,
            '0',
            str({
                28: 10,
                14: 10,
                3:  6,
                2:  4,
                1:  2,
                }[(self.finish - self.start).days]),
            '2',
            '1',
            # XXX See above note about 308<=>112
            str(308 if (self.interval.seconds // 60) == 112 else (self.interval.seconds // 60)),
            )) + '\r' +
            ''.join(str(head) for head in self.heads)).encode(ENCODING)

    def __unicode__(self):
        return str(self).decode(ENCODING)

    def refresh(self):
        if self.logger:
            data = self.logger._GPRB(self.serial)
            new = Bottle.from_string(data)
            self.serial = new.serial
            self.id = new.id
            self.start = new.start
            self.finish = new.finish
            self.interval = new.interval
            self.measurements = new.measurements
            self.mode = new.mode
            self.bottle_volume = new.bottle_volume
            self.sample_volume = new.sample_volume
            self.dilution = new.dilution
            self.heads = new.heads
            # Fix up the bottle references in the new heads list (they'll all
            # point to new when they should point to self as new is about to
            # get thrown away when we return)
            for head in self.heads:
                head.bottle = self
        else:
            raise RuntimeError(
                'Cannot refresh a bottle with no associated data logger')


class BottleHead(object):
    """
    Represents a single head on a gas bottle.

    `bottle` : the bottle this head belongs to
    `serial` : the serial number of the head
    `readings` : optional sequence of integers for the head's readings
    """

    def __init__(self, bottle, serial, pressure_limit=150, readings=None):
        self.bottle = bottle
        self.serial = serial
        self.pressure_limit = pressure_limit
        if readings is None or isinstance(readings, BottleReadings):
            self._readings = readings
        else:
            self._readings = BottleReadings(self, readings)

    @classmethod
    def from_string(cls, bottle, data):
        data = data.decode(ENCODING)
        # Strip trailing CR
        data = data.rstrip('\r')
        (   _,              # blank value (due to extraneous leading comma)
            serial,         # serial number of head
            pressure_limit, # pressure limit at which auto collection stops
            _,              # blank value (due to extraneous trailing comma)
        ) = data.split(',')
        return cls(bottle, serial, pressure_limit)

    def __str__(self):
        return (','.join((
            '',
            self.serial,
            str(self.pressure_limit),
            '',
            )) + '\r').encode(ENCODING)

    def __unicode__(self):
        return str(self).decode(ENCODING)

    @property
    def readings(self):
        if self._readings is None and self.bottle.logger is not None:
            data = self.bottle.logger._GMSK(
                ''.join(self.bottle.serial.split('-', 1)), self.serial)
            # XXX Check the first line includes the correct bottle and head
            # identifiers as specified, and that the reading count matches
            self._readings = BottleReadings.from_string(self, data)
        return self._readings

    def refresh(self):
        if self.bottle is not None and self.bottle.logger is not None:
            self._readings = None
        else:
            raise RuntimeError(
                'Cannot refresh a bottle head with no associated data logger')


class BottleReadings(object):
    """
    Represents the readings of a bottle head as a sequence-like object.

    `head` : the bottle head that the readings apply to
    `readings` : the readings for the head
    """

    def __init__(self, head, readings):
        self.head = head
        self._items = list(readings)

    @classmethod
    def from_string(cls, head, data):
        data = data.decode(ENCODING).split('\r')
        # Discard the empty line at the end
        assert not data[-1]
        data = data[:-1]
        (   head_serial,   # serial number of head
            bottle_serial, # serial number of the owning bottle
            _,             # ??? (always 1)
            _,             # ??? (always 1)
            _,             # ??? (0-247?)
            bottle_start,
            readings_len,
        ) = data[0].split(',')
        head_serial = str(int(head_serial))
        readings_len = int(readings_len)
        readings = cls(head, (
            int(value)
            for line in data[1:]
            for value in line.split(',')
            if value
            ))
        assert head_serial == head.serial
        assert '%s-%s' % (bottle_serial[:-2], bottle_serial[-2:]) == head.bottle.serial
        assert len(readings) == readings_len
        return readings

    def __str__(self):
        return (','.join((
            '%09d' % int(self.head.serial),
            ''.join(self.head.bottle.serial.split('-', 1)),
            '1',
            '1',
            '247', # can be zero, but we've no idea what this means...
            self.head.bottle.start.strftime(TIMESTAMP_FORMAT),
            str(len(self)),
            )) + '\r' +
            ''.join(
                ''.join(',%d' % reading for reading in chunk) + '\r'
                for chunk in [self[i:i + 10] for i in range(0, len(self), 10)]
                )
            ).encode(ENCODING)

    def __unicode__(self):
        return str(self).decode(ENCODING)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]


def moving_average(iterable, n):
    "Calculates a moving average of iterable over n elements"
    it = iter(iterable)
    d = deque(islice(it, n - 1))
    d.appendleft(0.0)
    s = sum(d)
    for elem in it:
        s += elem - d.popleft()
        d.append(elem)
        yield s / n


class DataAnalyzer(object):
    """
    Given a Bottle object, provides a moving average of head readings. The
    timestamps property provides a sequence of timestamps for the readings,
    while the heads property is a sequence of sequences of readings (the first
    dimension is the head, the second is the reading).

    `bottle` : the bottle to derive readings from
    `delta` : if True, return delta values instead of absolute pressures
    `points` : the number of points to average for each reading (must be odd)
    """

    def __init__(self, bottle, delta=False, points=1):
        self.bottle = bottle
        self._delta = delta
        self._points = points
        self._timestamps = None
        self._heads = None

    def refresh(self):
        self._timestamps = None
        self._heads = None
        self.bottle.refresh()

    def _get_delta(self):
        return self._delta

    def _set_delta(self, value):
        if value != self._delta:
            self._delta = bool(value)
            self._heads = None

    delta = property(_get_delta, _set_delta)

    def _get_points(self):
        return self._points

    def _set_points(self, value):
        if value != self._points:
            self._points = int(value)
            self._heads = None
            self._timestamps = None

    points = property(_get_points, _set_points)

    @property
    def timestamps(self):
        if self._timestamps is None:
            max_readings = max(len(head.readings) for head in self.bottle.heads)
            self._timestamps = [
                self.bottle.start + (
                    self.bottle.interval * (
                        reading + (self.points - 1) // 2))
                for reading in range(max_readings - (self.points - 1))
                ]
        return self._timestamps

    @property
    def heads(self):
        if self._heads is None:
            self._heads = [
                list(
                    moving_average((
                        reading - (head.readings[0] if self.delta else 0)
                        for reading in head.readings
                        ), self.points)
                    )
                for head in self.bottle.heads
                ]
        return self._heads


