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

import re
import time
import logging
from datetime import datetime, timedelta
from collections import deque
from itertools import islice
from threading import Thread

import serial


ENCODING = 'ascii'
TIMESTAMP_FORMAT = '%y%m%d%H%M%S'


class Error(Exception):
    """
    Base class for errors related to the data-logger
    """


class SendError(Error):
    """
    Exception raised due to a transmission error
    """


class HandshakeFailed(SendError):
    """
    Exception raised when the RTS/CTS handshake fails
    """


class PartialSend(SendError):
    """
    Exception raised when not all bytes of the message were sent
    """


class ReceiveError(Error):
    """
    Exception raise due to a reception error
    """


class UnexpectedReply(ReceiveError):
    """
    Exception raised when the data logger sends back an unexpected reply
    """


class ChecksumMismatch(ReceiveError):
    """
    Exception raised when a check-sum doesn't match the data sent
    """


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


class DataLogger(object):
    """
    Interfaces with the serial port of an OxiTop Data Logger and communicates
    with it when certain properties are queried for bottle or head information.

    `port` : a string representing the name of a serial port for the platform
    `timeout` : the number of seconds to wait for a response before timing out
    `retries` : the number of retries to attempt in the case of invalid data
    `progress` : (optional) triple of progress reporting functions (start, update, finish)
    """

    def __init__(self, port, retries=3, progress=None):
        super(DataLogger, self).__init__()
        self.port = port
        if self.port.timeout is None or self.port.timeout == 0:
            raise ValueError('serial port timeout must be a positive integer')
        self.retries = retries
        self._progress_start = self._progress_update = self._progress_finish = None
        if progress is not None:
            (   self._progress_start,
                self._progress_update,
                self._progress_finish,
            ) = progress
        self._bottles = None
        self._seen_prompt = False
        # Ensure the port is connected to an OC110 by requesting the
        # manufacturer's ID
        logging.debug('DTE: Testing for known response from MAID command')
        self.port.flushInput()
        self.id = self._MAID().rstrip('\r')
        if self.id != 'OC110':
            raise UnexpectedReply(
                'The connected unit is not an OxiTop OC110')

    def _tx(self, command, *args):
        """
        Sends a command (and optionally arguments) to the OC110. The command
        should not include the line terminator and the arguments should not
        include comma separators; this method takes care of command formatting.

        `command` : The command to send
        """
        # If we're not Clear To Send, set Ready To Send and wait for CTS to be
        # raised in response
        check_response = False
        response = ''
        self.port.setRTS()
        if not self.port.getCTS():
            logging.debug('DTE: CTS not set, setting RTS')
            cts_wait = time.time() + self.port.timeout
            while not self.port.getCTS():
                time.sleep(0.1)
                if time.time() > cts_wait:
                    raise HandshakeFailed(
                        'Failed to detect readiness with RTS/CTS handshake')
                    logging.debug('DTE: CTS set')
            # Read anything the unit sends through; if it's just booted up
            # there's probably some BIOS crap to ignore
            check_response = True
            response += self._rx(checksum=False)
        # If we've still not yet seen the ">" prompt, hit enter and see if we
        # get one back
        if not self._seen_prompt:
            logging.debug('DTE: No prompt seen, prodding unit with Enter')
            self.port.write('\r')
            check_response = True
            response += self._rx(checksum=False)
        # Because of the aforementioned BIOS crap, ignore everything but the
        # last line when checking for a response
        if check_response and not (response.endswith('LOGON\r') or
                response.endswith('INVALID COMMAND\r')):
            raise UnexpectedReply(
                'Expected LOGON or INVALID COMMAND, but got %s' % repr(response))
        data = ','.join([command] + [str(arg) for arg in args]) + '\r'
        logging.debug('DTE TX: %s' % data.rstrip('\r'))
        written = self.port.write(data)
        if written != len(data):
            raise PartialSend(
                'Only wrote first %d bytes of %d' % (written, len(data)))

    def _rx(self, checksum=True):
        """
        Receives a response from the OC110. If checksum is True, also checks
        that the transmitted checksum matches the transmitted data.

        `checksum` : If true, treat the last line of the repsonse as a checksum
        """
        response = ''
        if self._progress_start:
            self._progress_start()
        try:
            while '>\r' not in response:
                data = self.port.read().decode(ENCODING)
                if not data:
                    raise ReceiveError('Failed to read any data before timeout')
                elif data == '\n':
                    # Chuck away any LFs; these only appear in the BIOS output on
                    # unit startup and mess up line splits later on
                    continue
                elif data == '\r':
                    logging.debug('DTE RX: %s' % response.split('\r')[-1])
                    if self._progress_update:
                        self._progress_update()
                response += data
            self._seen_prompt = True
        finally:
            if self._progress_finish:
                self._progress_finish()
        # Split the response on the CRs and strip off the prompt at the end
        response = response.split('\r')[:-2]
        # If we're expecting a check-sum, check the last line for one and
        # ensure it matches the transmitted data
        if checksum:
            response, checksum_received = response[:-1], response[-1]
            if not checksum_received.startswith(','):
                raise UnexpectedReply('Checksum is missing leading comma')
            checksum_received = int(checksum_received.lstrip(','))
            checksum_calculated = sum(
                ord(c) for c in
                ''.join(line + '\r' for line in response)
                )
            if checksum_received != checksum_calculated:
                raise ChecksumMismatch('Checksum does not match data')
        # Return the reconstructed response (without prompt or checksum)
        return ''.join(line + '\r' for line in response)

    def _MAID(self):
        """
        Sends a MAID (MAnufacturer ID) command to the OC110 and returns the
        response.
        """
        self._tx('MAID')
        return self._rx(checksum=False)

    def _CLOC(self):
        """
        Sends a CLOC (CLOse Connection) command to the OC110 and sets RTS to
        low (indicating we're going to stop talking to it).
        """
        self._tx('CLOC')
        self._rx()
        self.port.setRTS(level=False)
        self._seen_prompt = False

    def _GAPB(self):
        """
        Sends a GAPB (Get All Pressure Bottles) command to the OC110 and
        returns the data received.
        """
        for retry in range(self.retries):
            try:
                self._tx('GAPB')
                return self._rx()
            except ChecksumMismatch as exc:
                e = exc
        raise e

    def _GPRB(self, bottle):
        """
        Sends a GPRB (Get PRessure Bottle) command to the OC110 and returns
        the data received.
        """
        for retry in range(self.retries):
            try:
                self._tx('GPRB', bottle)
                return self._rx()
            except ChecksumMismatch as exc:
                e = exc
        raise e

    def _GSNS(self, bottle):
        """
        Sends a GSNS (???) command to the OC110. No idea what this command
        does but the original software always used it between GPRB and GMSK.
        """
        self._tx('GSNS', bottle)
        self._rx(checksum=False)

    def _GMSK(self, bottle, head):
        """
        Sends a GMSK (Get ... erm ... bottle head readings - no idea how they
        get MSK out of that) command to the OC110. Returns the data received.
        """
        for retry in range(self.retries):
            try:
                self._tx('GMSK', bottle, head)
                return self._rx()
            except ChecksumMismatch as exc:
                e = exc
        raise e

    @property
    def bottles(self):
        """
        Return all bottles stored on the connected device.
        """
        if self._bottles is None:
            # Use the GAPB command to retrieve the details of all bottles
            # stored in the device
            data = self._GAPB()
            self._bottles = []
            bottle = ''
            # Split the response into individual bottles and their head line(s)
            for line in data.split('\r')[:-1]:
                if not line.startswith(','):
                    if bottle:
                        self._bottles.append(
                            Bottle.from_string(bottle, logger=self))
                    bottle = line + '\r'
                else:
                    bottle += line + '\r'
            if bottle:
                self._bottles.append(
                    Bottle.from_string(bottle, logger=self))
        return self._bottles

    def bottle(self, serial):
        """
        Return a bottle with a specific serial number.

        `serial` : the serial number of the bottle to retrieve
        """
        # Check for the specific serial number without refreshing the entire
        # list. If it's there, return it from the list.
        if self._bottles is not None:
            for bottle in self._bottles:
                if bottle.serial == serial:
                    return bottle
        # Otherwise, use the GPRB to retrieve individual bottle details. Note
        # that we DON'T add it to the list in this case as the list may be
        # uninitialized at this point. Even if we initialized it, a future call
        # would have no idea the list was only partially populated
        data = self._GPRB(serial)
        return Bottle.from_string(data, logger=self)

    def refresh(self):
        """
        Force the details of all bottles to be re-read on next access.
        """
        self._bottles = None


class DummyLogger(Thread):
    """
    Emulates an OxiTop OC110 Data Logger for testing. Can be combined with
    DummySerial below for a complete testing solution without having to involve
    a physical serial port.

    `port` : the serial port that the emulated data logger should listen to
    """

    def __init__(self, port):
        super(DummyLogger, self).__init__()
        self.terminated = False
        self.daemon = True
        self.port = port
        assert self.port.timeout > 0
        assert self.port.bytesize == serial.EIGHTBITS
        assert self.port.parity == serial.PARITY_NONE
        assert self.port.stopbits == serial.STOPBITS_ONE
        # Set up the list of gas bottles and pressure readings
        self.bottles = []
        self.bottles.append(Bottle(
            serial='110222-06',
            id=999,
            start=datetime(2011, 2, 22, 16, 54, 55),
            finish=datetime(2011, 3, 8, 16, 54, 55),
            interval=timedelta(seconds=56 * 60),
            expected_measurements=360,
            mode='pressure',
            bottle_volume=510,
            sample_volume=432,
            dilution=0
            ))
        self.bottles[-1].heads.append(BottleHead(
            self.bottles[-1],
            serial='60108',
            readings=[
                970, 965, 965, 965, 965, 965, 964, 965, 965, 965, 965, 964,
                965, 965, 965, 965, 965, 965, 964, 965, 965, 965, 965, 965,
                964, 965, 965, 964, 964, 964, 965, 965, 965, 965, 965, 965,
                965, 965, 964, 964, 965, 965, 965, 964, 965, 965, 965, 965,
                965, 965, 965, 965, 965, 965, 965, 964, 964, 964, 965, 965,
                965, 965, 965, 964, 964, 964, 964, 965, 965, 965, 965, 965,
                964, 964, 964, 964, 964, 964, 965, 965, 965, 965, 965, 964,
                964, 964, 964, 964, 965, 965, 964, 964, 964, 965, 965, 964,
                965, 965, 964, 964, 965, 964, 964, 964, 965, 965, 964, 964,
                964, 965, 965, 964, 964, 964, 965, 964, 964, 964, 964, 965,
                964, 965, 965, 964, 964, 965, 965, 964, 964, 964, 964, 964,
                965, 964, 965, 965, 964, 965, 965, 964, 965, 964, 965, 965,
                965, 964, 965, 964, 964, 964, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 965, 965,
                964, 964, 964, 964, 964, 965, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 965, 965, 964, 965, 964, 964, 965, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 963, 963, 964,
                963, 963, 964, 964, 964, 964, 964, 964, 963, 964, 964, 964,
                964, 964, 964, 964, 964, 963, 963, 963, 963, 964, 964, 964,
                964, 963, 963, 964, 964, 964, 963, 963, 963, 964, 963, 964,
                964, 964, 964, 964, 964, 963, 963, 963, 963, 963, 963, 963,
                963, 963, 963, 963, 963, 963, 963, 963, 964, 964, 963, 963,
                963, 963, 963, 963, 963, 964, 963, 963, 963, 963, 963, 962,
                962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962,
                961, 962, 962, 962, 963, 962, 962, 962, 962, 962, 962, 962,
                962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 961,
                962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 961,
                962,
                ]))
        self.bottles.append(Bottle(
            serial='121119-03',
            id=3,
            start=datetime(2012, 11, 19, 13, 53, 4),
            finish=datetime(2012, 11, 22, 13, 53, 4),
            interval=timedelta(seconds=12 * 60),
            expected_measurements=360,
            mode='pressure',
            bottle_volume=510,
            sample_volume=432,
            dilution=0
            ))
        self.bottles[-1].heads.append(BottleHead(
            self.bottles[-1],
            serial='60108',
            readings=[]))
        self.bottles.append(Bottle(
            serial='120323-01',
            id=1,
            start=datetime(2012, 3, 23, 17, 32, 23),
            finish=datetime(2012, 4, 20, 17, 32, 23),
            interval=timedelta(seconds=112 * 60),
            expected_measurements=360,
            mode='pressure',
            bottle_volume=510,
            sample_volume=432,
            dilution=0
            ))
        self.bottles[-1].heads.append(BottleHead(
            self.bottles[-1],
            serial='60145',
            readings=[
                976, 964, 963, 963, 963, 963, 963, 963, 963, 963, 963, 963,
                963, 963, 964, 963, 963, 963, 963, 963, 963, 963, 963, 963,
                962, 963, 963, 962, 962, 963, 963, 963, 963, 962, 963, 963,
                963, 962, 962, 963, 962, 963, 963, 962, 962, 963, 963, 963,
                963, 962, 962, 963, 963, 963, 962, 963, 963, 963, 963, 962,
                962, 962, 963, 962, 963, 962, 962, 963, 963, 962, 962, 962,
                962, 963, 962, 962, 962, 962, 963, 963, 962, 963, 963, 963,
                962, 962, 962, 962, 963, 962, 962, 962, 962, 962, 962, 962,
                962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 963, 962,
                962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962,
                962, 961, 962, 961, 962, 962, 962, 962, 962, 962, 962, 961,
                962, 961, 961, 962, 961, 962, 962, 962, 962, 961, 962, 962,
                961, 962, 962, 961, 962, 961, 962, 961, 962, 961, 962, 961,
                962, 961, 962, 961, 962, 961, 962, 961, 961, 961, 962, 961,
                962, 962, 961, 962, 962, 961, 961, 961, 962, 961, 961, 962,
                962, 961, 962, 961, 961, 961, 961, 961, 962, 961, 961, 961,
                961, 962, 961, 962, 961, 961, 962, 961, 961, 962, 961, 961,
                961, 961, 961, 961, 961, 961, 961, 961, 961, 961, 961, 961,
                962, 961, 960, 961, 961, 961, 961, 960, 961, 961, 960, 961,
                961, 961, 961, 961, 961, 961, 961, 961, 961, 961, 961, 961,
                961, 961, 960, 961, 960, 961, 961, 960, 961, 960, 961, 960,
                960, 960, 961, 961, 960, 961, 960, 961, 961, 960, 961, 960,
                961, 960, 961, 960, 960, 960, 961, 960, 960, 961, 961, 961,
                960, 961, 960, 960, 961, 960, 960, 961, 960, 960, 960, 960,
                961, 960, 960, 960, 960, 960, 960, 961, 960, 960, 960, 960,
                960, 960, 960, 959, 960, 959, 960, 960, 959, 960, 960, 960,
                960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960, 960,
                960, 959, 960, 959, 960, 960, 959, 960, 960, 959, 960, 960,
                959, 960, 959, 959, 960, 959, 959, 959, 960, 960, 960, 959,
                959, 960, 959, 960, 960, 959, 960, 959, 959, 960, 959, 959,
                960,
                ]))
        self.bottles[-1].heads.append(BottleHead(
            self.bottles[-1],
            serial='60143',
            readings=[
                970, 965, 965, 965, 965, 965, 964, 965, 965, 965, 965, 964,
                965, 965, 965, 965, 965, 965, 964, 965, 965, 965, 965, 965,
                964, 965, 965, 964, 964, 964, 965, 965, 965, 965, 965, 965,
                965, 965, 964, 964, 965, 965, 965, 964, 965, 965, 965, 965,
                965, 965, 965, 965, 965, 965, 965, 964, 964, 964, 965, 965,
                965, 965, 965, 964, 964, 964, 964, 965, 965, 965, 965, 965,
                964, 964, 964, 964, 964, 964, 965, 965, 965, 965, 965, 964,
                964, 964, 964, 964, 965, 965, 964, 964, 964, 965, 965, 964,
                965, 965, 964, 964, 965, 964, 964, 964, 965, 965, 964, 964,
                964, 965, 965, 964, 964, 964, 965, 964, 964, 964, 964, 965,
                964, 965, 965, 964, 964, 965, 965, 964, 964, 964, 964, 964,
                965, 964, 965, 965, 964, 965, 965, 964, 965, 964, 965, 965,
                965, 964, 965, 964, 964, 964, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 965, 965,
                964, 964, 964, 964, 964, 965, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 965, 965, 964, 965, 964, 964, 965, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964, 964,
                964, 964, 964, 964, 964, 964, 964, 964, 964, 963, 963, 964,
                963, 963, 964, 964, 964, 964, 964, 964, 963, 964, 964, 964,
                964, 964, 964, 964, 964, 963, 963, 963, 963, 964, 964, 964,
                964, 963, 963, 964, 964, 964, 963, 963, 963, 964, 963, 964,
                964, 964, 964, 964, 964, 963, 963, 963, 963, 963, 963, 963,
                963, 963, 963, 963, 963, 963, 963, 963, 964, 964, 963, 963,
                963, 963, 963, 963, 963, 964, 963, 963, 963, 963, 963, 962,
                962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962,
                961, 962, 962, 962, 963, 962, 962, 962, 962, 962, 962, 962,
                962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 961,
                962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 962, 961,
                962,
                ]))
        # Start the emulator thread
        self.start()

    def run(self):
        """
        The main method of the background thread. Waits for OC110 commands and
        acts upon them when received.
        """
        buf = ''
        if not self.port.isOpen():
            self.port.open()
        # On start-up, device sends some BIOS crap, regardless of whether or
        # not anything is listening
        self.port.setRTS()
        self.port.write('\0\r\n')
        self.port.write('BIOS OC Version 1.0\r\n')
        while not self.terminated:
            print('Running')
            buf += self.port.read().decode('ASCII')
            while '\r' in buf:
                command, buf = buf.split('\r', 1)
                logging.debug('DCE RX: %s' % command)
                if ',' in command:
                    command = command.split(',')
                    command, args = command[0], command[1:]
                else:
                    args = []
                self.handle(command, *args)

    def send(self, data, checksum=False):
        """
        Sends data over the serial port with an optional checksum suffix. The
        method ensures the port is open, RTS is set, and CTS is received before
        beginning transmission.
        """
        # Wait up to the port's timeout for CTS
        if not self.port.getCTS():
            self.port.setRTS()
            cts_wait = time.time() + self.port.timeout
            while not self.port.getCTS():
                time.sleep(0.1)
                if time.time() > cts_wait:
                    raise ValueError(
                        'Failed to detect readiness with RTS/CTS handshake')
        for line in data.strip('\r').split('\r'):
            logging.debug('DCE TX: %s' % line)
        self.port.write(data)
        if checksum:
            value = sum(ord(c) for c in data)
            self.send(',%d\r' % value, checksum=False)

    def handle(self, command, *args):
        """
        Executes the OC110 ``command`` with the specified ``args``
        """
        if command == 'MAID':
            # MAnufacturer IDentifier; OC110 sends 'OC110'
            self.send('OC110\r')
        elif command == 'CLOC':
            # CLOse Connection; OC110 sends a return, a prompt, pauses, then
            # sends a NUL char, and finally the 'LOGON' prompt
            self.send('\r')
            self.send('>\r')
            self.port.setRTS(False)
            self.port.close()
            # Emulate the unit taking a half second to reboot
            time.sleep(0.5)
            self.port.write('LOGON\r')
        elif command == 'GAPB':
            # Get All Pressure Bottles command returns the header details of
            # all bottles and their heads
            data = ''.join(str(bottle) for bottle in self.bottles)
            self.send(data, checksum=True)
        elif command == 'GPRB':
            # Get PRessure Bottle command returns the details of the specified
            # bottle and its heads
            if len(args) != 1:
                self.send('INVALID ARGS\r')
            else:
                try:
                    bottle = self.bottle_by_serial(args[0])
                except ValueError:
                    self.send('INVALID BOTTLE\r')
                else:
                    self.send(str(bottle), checksum=True)
        elif command == 'GSNS':
            # No idea what GSNS does. Accepts a bottle serial and returns
            # nothing...
            if len(args) != 1:
                self.send('INVALID ARGS\r')
            else:
                try:
                    bottle = self.bottle_by_serial(args[0])
                except ValueError:
                    self.send('INVALID BOTTLE\r')
        elif command.startswith('GMSK'):
            # GMSK returns all readings from a specified bottle head
            if len(args) != 2:
                self.send('INVALID ARGS\r')
            else:
                try:
                    bottle = self.bottle_by_serial(args[0])
                except ValueError:
                    self.send('INVALID BOTTLE\r')
                for head in bottle.heads:
                    if head.serial == args[1]:
                        break
                    head = None
                if not head:
                    self.send('INVALID HEAD\r')
                self.send(str(head.readings), checksum=True)
        else:
            self.send('INVALID COMMAND\r')
        self.send('>\r')

    def bottle_by_serial(self, serial):
        if '-' not in serial:
            serial = '%s-%s' % (serial[:-2], serial[-2:])
        for bottle in self.bottles:
            if bottle.serial == serial:
                return bottle
        raise ValueError('%s is not a valid bottle serial number')


class NullModem(object):
    """
    Emulates one end of a null modem. Don't construct this class directly, but
    use the null_modem routine below to construct both ends of the null-modem.
    All parameters are equivalent to the pyserial Serial class.
    """

    def __init__(self, port=None, baudrate=9600, bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            timeout=None, xonxoff=False, rtscts=False, writeTimeout=None,
            dsrdtr=False, interCharTimeout=None):
        super(NullModem, self).__init__()
        self.port = port
        self.name = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self.dsrdtr = dsrdtr
        self.writeTimeout = writeTimeout
        self.interCharTimeout = interCharTimeout
        self._other = None
        self._rts = False
        self._dtr = False
        self._buf = [] # XXX Should use a deque for this
        self._opened = bool(self.port)

    def readable(self):
        return True

    def writeable(self):
        return True

    def seekable(self):
        return False

    def open(self):
        assert not self._opened
        self._opened = True

    def close(self):
        assert self._opened
        self._opened = False

    def isOpen(self):
        return self._opened

    def flush(self):
        pass

    def flushInput(self):
        self._buf = []

    def flushOutput(self):
        pass

    def nonblocking(self):
        raise NotImplementedError

    def fileno(self):
        raise NotImplementedError

    def setXON(self, level=True):
        raise NotImplementedError

    def sendBreak(self, duration=0.25):
        raise NotImplementedError

    def setBreak(self, level=True):
        raise NotImplementedError

    def setRTS(self, level=True):
        self._rts = level

    def getCTS(self):
        return self._other._rts

    def setDTR(self, level=True):
        self._dtr = level

    def getDSR(self):
        return self._other.dtr

    def getCD(self):
        raise self._other.dtr

    def getRI(self):
        raise NotImplementedError

    def readinto(self, b):
        # XXX Should implement this from read()
        raise NotImplementedError

    def inWaiting(self):
        return len(self._buf)

    def read(self, size=1):
        assert self._opened
        start = time.time()
        now = start
        result = ''
        while len(result) < size:
            if self._buf:
                result += self._buf[0]
                del self._buf[0]
            else:
                time.sleep(0.1)
            now = time.time()
            if self.timeout is not None and now > start + self.timeout:
                break
        assert len(result) <= size
        return result

    def write(self, data):
        assert self._opened
        for byte in data:
            self._other._buf.append(byte)
            # Pause for the amount of time it would take to send data
            time.sleep(1.0 / self.baudrate)
        return len(data)


def null_modem(
        baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE, timeout=None, xonxoff=False,
        rtscts=False, writeTimeout=None, dsrdtr=False, interCharTimeout=None):
    """
    Construct both ends of a null-modem cable, returning a tuple of two serial
    ports. All parameters are the same as the pyserial Serial class.
    """
    port1 = NullModem(
            'TEST', baudrate, bytesize, parity, stopbits, timeout,
            xonxoff, rtscts, writeTimeout, dsrdtr, interCharTimeout
            )
    port2 = NullModem(
            'TEST', baudrate, bytesize, parity, stopbits, timeout,
            xonxoff, rtscts, writeTimeout, dsrdtr, interCharTimeout
            )
    port1._other = port2
    port2._other = port1
    return (port1, port2)

