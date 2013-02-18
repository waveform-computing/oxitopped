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
`DataLogger` (see the `oxitopdump.logger` module).
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

from datetime import datetime, timedelta
from collections import deque
from itertools import islice
from xml.etree.ElementTree import fromstring, tostring, Element, SubElement

import serial


ENCODING = 'ascii'
TIMESTAMP_FORMAT = '%y%m%d%H%M%S'


def xml(e, **args):
    return e.__xml__(**args)


class Bottle(object):
    """
    Represents a bottle as collected from an OxiTop OC110 Data Logger.

    `serial` : the bottle serial number
    `id` : additional user-assigned ID number (1-999), non-unique
    `start` : the timestamp at the start of the run
    `finish` : the timestamp at the end of the run
    `measurements` : the expected number of measurements
    `mode` : one of 'pressure' or 'bod'
    `bottle_volume` : the nominal volume (in ml) of the bottle
    `sample_volume` : the volume of the sample (in ml) within the bottle
    `dilution` : the dilution of the sample (1+value)
    `logger` : a DataLogger instance that can be used to update the bottle
    """

    def __init__(
            self, serial, id, start, finish, measurements, mode, bottle_volume,
            sample_volume, dilution, logger=None):
        self.logger = logger
        try:
            date, num = serial[:-2], serial[-2:]
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
        self.expected_measurements = measurements
        self.interval = (finish - start) // measurements
        self.mode = mode
        self.bottle_volume = float(bottle_volume)
        self.sample_volume = float(sample_volume)
        self.dilution = dilution
        self.heads = []

    @property
    def actual_measurements(self):
        return max(len(head.auto_readings) for head in self.heads)

    @property
    def mode_string(self):
        prefix = (
            'Pressure' if self.mode == 'pressure' else
            'BOD' if self.mode == 'bod' else
            'Unknown'
            )
        duration = self.finish - self.start
        if duration.days > 0:
            suffix = '%dd' % duration.days
        else:
            suffix = '%dh' % (duration.seconds // 3600)
        return '%s %s' % (prefix, suffix)

    @property
    def completed(self):
        return 'Yes' if self.finish < datetime.now() else 'No'

    @classmethod
    def from_xml(cls, data, logger=None):
        bottle_elem = fromstring(data)
        assert bottle_elem.tag == 'bottle'
        bottle = cls(
            bottle_elem.attrib['serial'],
            int(bottle_elem.attrib['id']),
            datetime.strptime(bottle_elem.attrib['start'], '%Y-%m-%dT%H:%M:%S'),
            datetime.strptime(bottle_elem.attrib['finish'], '%Y-%m-%dT%H:%M:%S'),
            int(bottle_elem.attrib['measurements']),
            bottle_elem.attrib['mode'],
            float(bottle_elem.attrib['bottlevolume']),
            float(bottle_elem.attrib['samplevolume']),
            int(bottle_elem.attrib['dilution']),
            logger
            )
        for head_elem in bottle_elem.findall('head'):
            auto_readings_elem = head_elem.find('autoreadings')
            if auto_readings_elem is not None:
                auto_readings = [
                    int(reading.attrib['value'])
                    for reading in auto_readings_elem.findall('reading')
                    ]
            else:
                auto_readings = []
            manual_readings_elem = head_elem.find('manualreadings')
            if manual_readings_elem is not None:
                manual_readings = [
                    (
                        bottle.start + timedelta(seconds=int(reading.attrib['timestamp'])),
                        int(reading.attrib['value'])
                        )
                    for reading in manual_readings_elem.findall('reading')
                    ]
            else:
                manual_readings = []
            head = BottleHead(
                bottle,
                head_elem.attrib['serial'],
                int(head_elem.attrib['pressurelimit'])
                    if 'pressurelimit' in head_elem.attrib else None,
                auto_readings,
                manual_readings
                )
            bottle.heads.append(head)
        return bottle

    def __xml__(self):
        bottle_elem = Element('bottle', attrib=dict(
            serial=self.serial,
            id=str(self.id),
            start=self.start.isoformat(),
            finish=self.finish.isoformat(),
            measurements=str(self.expected_measurements),
            mode=self.mode,
            bottlevolume=str(self.bottle_volume),
            samplevolume=str(self.sample_volume),
            dilution=str(self.dilution),
            ))
        for head in self.heads:
            head_elem = SubElement(bottle_elem, 'head', attrib=dict(
                serial=head.serial,
                ))
            if head.pressure_limit is not None:
                head_elem.attrib['pressurelimit'] = str(head.pressure_limit)
            auto_readings_elem = SubElement(head_elem, 'autoreadings')
            for reading in head.auto_readings:
                e = SubElement(auto_readings_elem, 'reading')
                e.attrib['value'] = str(reading)
            manual_readings_elem = SubElement(head_elem, 'manualreadings')
            for timestamp, reading in head.manual_readings:
                e = SubElement(manual_readings_elem, 'reading')
                e.attrib['timestamp'] = str((timestamp - self.start).seconds)
                e.attrib['value'] = str(reading)
        return tostring(bottle_elem)

    @classmethod
    def from_string(cls, data, logger=None):
        data = data.decode(ENCODING).split('\r')
        # Discard the empty line(s) at the end
        while data and not data[-1]:
            data = data[:-1]
        # Ensure there are exactly two lines
        assert len(data) == 2
        # Parse the first line for bottle information
        (   _,             # ???
            _,             # ???
            mode,          # mode (0==bod, 3==pressure, 1=???, 2=???)
            id,            # I.D. No.
            serial,        # bottle serial number
            start,         # start timestamp (YYMMDDhhmmss)
            finish,        # finish timestamp (YYMMDDhhmmss)
            _,             # ??? see notes in __str__
            _,             # ???
            _,             # ???
            _,             # ???
            measurements,  # number of measurements
            duration,      # duration (minutes)
            bottle_volume, # bottle volume (ml)
            sample_volume, # sample volume (ml)
            _,             # ??? see notes in __str__
            _,             # ???
            _,             # ???
            heads,         # number of heads
            interval,      # ??? see notes in __str__
            ) = data[0].split(',')
        bottle = cls(
            serial,
            int(id),
            datetime.strptime(start, TIMESTAMP_FORMAT),
            datetime.strptime(finish, TIMESTAMP_FORMAT),
            int(measurements),
            {
                '0': 'bod',
                '3': 'pressure',
            }[mode],
            float(bottle_volume),
            float(sample_volume),
            0,
            logger
            )
        # Parse second line as BottleHead data
        serials = data[1].split(',')[1:-1]
        if bottle.mode == 'bod':
            for serial in serials:
                bottle.heads.append(BottleHead(bottle, serial))
        elif bottle.mode == 'pressure':
            serials = zip(serials[0::2], serials[1::2])
            for serial, pressure_limit in serials:
                bottle.heads.append(BottleHead(bottle, serial, int(pressure_limit)))
        return bottle

    def __str__(self):
        return (','.join((
            '0',
            '0',
            {
                # XXX Need to test BOD special vs routine vs standard
                'bod': '0',
                'pressure': '3',
                }[self.mode],
            str(self.id),
            self.serial,
            self.start.strftime(TIMESTAMP_FORMAT),
            self.finish.strftime(TIMESTAMP_FORMAT),
            # XXX Seems to be 1 for unfinished samples, 2 for finished samples.
            # Perhaps 0 is samples yet to start? Also not sure if it matters
            # whether samples have been downloaded to the unit yet or not
            str(2 if self.finish < datetime.now() else 1),
            '5',
            '240',
            '40',
            str(self.expected_measurements),
            str((self.finish - self.start).days * 24 * 60),
            '%.0f' % self.bottle_volume,
            '%.1f' % self.sample_volume,
            # XXX This might be dilution. Always seems to be zero so far and
            # we haven't tested varying the dilution setting. However, could be
            # the auto-temp setting as well...
            '0',
            # XXX This is probably the duration of the auto-temp adaptation
            # phase. Disabled for runs less than 1 day, limited to 70 minutes
            # for runs longer than 5 days. Specified in 7s of minutes (?!)
            str(
                0 if (self.finish - self.start).days == 0 else
                10 if (self.finish - self.start).days >= 5 else
                2 * (self.finish - self.start).days
                ),
            '2',
            str(len(self.heads)),
            # XXX No idea how this last field is constructed. In pressure mode
            # it *seems* to be the interval between readings in minutes, but
            # 112 minute intervals are reported as 308 (?!). Meanwhile in BOD
            # standard mode it seems to be 32768 + runtime in hours. Might be a
            # bit-field but that doesn't seem to fit the 308<=>112 thing and it
            # only partially fits the BOD standard mode def.
            str(
                (308 if (self.interval.seconds // 60) == 112 else (self.interval.seconds // 60))
                if self.mode == 'pressure' else
                32768 +
                ((self.finish - self.start).days * 24) + 
                ((self.finish - self.start).seconds // 3600)
                ),
            )) +
            '\r' +
            ','.join([''] + [
                    '%s,%d' % (head.serial, head.pressure_limit)
                    if self.mode == 'pressure' else
                    head.serial
                    for head in self.heads
                    ] + ['']) +
            '\r').encode(ENCODING)

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
    `pressure_limit` : the pressure limit for heads run in pressure mode
    `auto_readings` : optional sequence of integers for the head's auto-readings
    `manual_readings` : optional sequence of (timestamp, reading) tuples
    """

    def __init__(
            self, bottle, serial, pressure_limit=None, auto_readings=None,
            manual_readings=None):
        self.bottle = bottle
        self.serial = serial
        self.pressure_limit = pressure_limit
        if auto_readings:
            self.auto_readings = auto_readings
        else:
            self.auto_readings = []
        if manual_readings:
            self.manual_readings = manual_readings
        else:
            self.manual_readings = []

    def __unicode__(self):
        return str(self).decode(ENCODING)

    def _get_auto_readings(self):
        if self._auto_readings is None and self.bottle.logger is not None:
            data = self.bottle.logger._GMSK(self.bottle.serial, self.serial)
            # XXX Check the first line includes the correct bottle and head
            # identifiers as specified
            self._auto_readings = BottleAutoReadings.from_string(self, data)
        return self._auto_readings

    def _set_auto_readings(self, value):
        if isinstance(value, BottleAutoReadings):
            self._auto_readings = value
            self._auto_readings.head = self
        else:
            self._auto_readings = BottleAutoReadings(self, value)

    auto_readings = property(_get_auto_readings, _set_auto_readings)

    def _get_manual_readings(self):
        if self._manual_readings is None and self.bottle.logger is not None:
            if self.bottle.mode == 'pressure':
                # Manual (momentary) readings can only be taken in pressure
                # mode. As this mode can only operate with a single head, we
                # don't specify the head here
                data = self.bottle.logger._GSNS(self.bottle.serial)
            else:
                data = []
            self._manual_readings = BottleManualReadings.from_string(self, data)
        return self._manual_readings

    def _set_manual_readings(self, value):
        if isinstance(value, BottleManualReadings):
            self._manual_readings = value
            self._manual_readings.head = self
        else:
            self._manual_readings = BottleManualReadings(self, value)

    manual_readings = property(_get_manual_readings, _set_manual_readings)

    def refresh(self):
        if self.bottle is not None and self.bottle.logger is not None:
            self._auto_readings = None
            self._manual_readings = None
        else:
            raise RuntimeError(
                'Cannot refresh a bottle head with no associated data logger')


class BottleManualReadings(object):
    """
    Represents the momentary values of a bottle head as a sequence of
    (timestamp, value) tuples.

    `head` : the bottle head that the readings apply to
    `readings` : a sequence of (timestamp, value) tuples for the head
    """

    def __init__(self, head, readings):
        self.head = head
        self._items = list(readings)

    @classmethod
    def from_string(cls, head, data):
        data = data.decode(ENCODING).split('\r')
        # Discard the empty line(s) at the end
        while data and not data[-1]:
            data = data[:-1]
        if data:
            readings_len, _ = data[0].split(',', 1)
            readings_len = int(readings_len)
            assert len(data) == readings_len + 1
            data = [line.split(',') for line in data[1:]]
        else:
            data = []
        readings = cls(head, (
            (head.bottle.start + timedelta(seconds=int(timestamp)), int(value))
            for (timestamp, value, _) in data
            ))
        return readings

    def __str__(self):
        if self:
            return (
                '%d,\r' % len(self) +
                ''.join(
                    '%d,%d,\r' % ((timestamp - self.head.bottle.start).seconds, value)
                    for (timestamp, value) in self
                    )
                ).encode(ENCODING)
        else:
            return ''

    def __unicode__(self):
        return str(self).decode(ENCODING)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]


class BottleAutoReadings(object):
    """
    Represents the auto-readings of a bottle head as a sequence-like object.

    `head` : the bottle head that the readings apply to
    `readings` : the readings for the head
    """

    def __init__(self, head, readings):
        self.head = head
        self._items = list(readings)

    @classmethod
    def from_string(cls, head, data):
        data = data.decode(ENCODING).split('\r')
        # Discard the empty line(s) at the end
        while data and not data[-1]:
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
        assert bottle_serial == head.bottle.serial
        assert len(readings) == readings_len
        return readings

    def __str__(self):
        return (','.join((
            '%09d' % int(self.head.serial),
            self.head.bottle.serial,
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
        self._manual = False
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

    def _get_manual(self):
        return self._manual

    def _set_manual(self, value):
        if value != self._manual:
            self._manual = bool(value)
            self._heads = None
            self._timestamps = None

    manual = property(_get_manual, _set_manual)

    @property
    def timestamps(self):
        if self._timestamps is None:
            max_readings = max(len(head.auto_readings) for head in self.bottle.heads)
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
                        reading - (head.auto_readings[0] if self.delta else 0)
                        for reading in head.auto_readings
                        ), self.points)
                    )
                for head in self.bottle.heads
                ]
        return self._heads


