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

from datetime import datetime, timedelta
import time
import logging

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
    `pressure` : the "pressure type" (what does this mean?)
    `bottle_volume` : the nominal volume (in ml) of the bottle
    `sample_volume` : the volume of the sample (in ml) within the bottle
    `logger` : a DataLogger instance that can be used to update the bottle
    """

    def __init__(
            self, serial, id, start, finish, interval, pressure, bottle_volume,
            sample_volume, dilution, logger=None):
        self.logger = logger
        self.serial = serial
        self.id = id
        self.start = start
        self.finish = finish
        self.interval = interval
        self.pressure = pressure
        self.bottle_volume = bottle_volume
        self.sample_volume = sample_volume
        self.dilution = dilution
        self.heads = []

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
            pressure,      # pressure type
            bottle_volume, # bottle volume (ml)
            sample_volume, # sample volume (ml)
            _,             # ???
            _,             # ???
            _,             # ???
            _,             # number of heads, perhaps???
            interval,      # interval of readings
        ) = data[0].split(',')
        bottle = cls(
            serial,
            int(id),
            datetime.strptime(start, TIMESTAMP_FORMAT),
            datetime.strptime(finish, TIMESTAMP_FORMAT),
            # For some reason, intervals of 112 minutes are reported as 308?!
            timedelta(seconds=60 * int(112 if interval == 308 else interval)),
            int(pressure) // (24 * 60),
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
            str(self.serial),
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

    def refresh(self):
        if self.logger:
            data = self.logger._GPRB(self.serial)
            new = Bottle.from_string(data)
            self.serial = new.serial
            self.id = new.id
            self.start = new.start
            self.finish = new.finish
            self.interval = new.interval
            self.pressure = new.pressure
            self.bottle_volume = new.bottle_volume
            self.sample_volume = new.sample_volume
            self.dilution = new.dilution
            self.heads = new.heads


class BottleHead(object):
    """
    Represents a single head on a gas bottle.

    `bottle` : the bottle this head belongs to
    `serial` : the serial number of the head
    """

    def __init__(self, bottle, serial, readings=None):
        self.bottle = bottle
        self.serial = serial
        self._readings = readings

    @classmethod
    def from_string(cls, bottle, data):
        data = data.decode(ENCODING)
        (   _,      # blank value (due to extraneous leading comma)
            serial, # serial number of head
            _,      # ???
            _,      # blank value (due to extraneous trailing comma)
        ) = data.split(',')
        return cls(bottle, serial)

    def __str__(self):
        return (','.join((
            '',
            self.serial,
            '150',
            '',
            )) + '\r').encode(ENCODING)

    def __unicode__(self):
        return str(self).decode(ENCODING)

    @property
    def readings(self):
        if self._readings is None and self.bottle.logger is not None:
            data = self.bottle.logger._GMSK(self.bottle.serial, self.serial)
            # XXX Check the first line includes the correct bottle and head
            # identifiers as specified, and that the reading count matches
            data = data[1:]
            self._readings = [
                int(value)
                for line in data.split('\r')
                for value in line.split(',')
                if value
                ]
        return self._readings


class BottleHeadReadings(list):
    def __init__(self, head, *args):
        self.head = head
        super(BottleHeadReadings, self).__init__(*args)

    def refresh(self):
        self.clear()

class DataLogger(object):
    """
    Interfaces with the serial port of an OxiTop OC110 Data Logger and
    communicates with it when certain properties are queried for bottle or
    head information.

    `port` : a serial.Serial object (or compatible)
    """

    def __init__(self, port):
        if not port.timeout:
            raise ValueError(
                'The port is not set for blocking I/O with a non-zero timeout')
        self.port = port
        self._bottles = None
        self._seen_prompt = False
        # Ensure the port is connected to an OC110 by requesting the
        # manufacturer's ID
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
        if not self.port.getCTS():
            cts_wait = time.time() + self.port.timeout
            self.port.setRTS()
            while not self.port.getCTS():
                time.sleep(0.1)
                if time.time() > cts_wait:
                    raise HandshakeFailed(
                        'Failed to detect readiness with RTS/CTS handshake')
            # Read anything the unit sends through; if it's just booted up
            # there's probably some BIOS crap to ignore
            check_response = True
            response += self._rx(checksum=False)
        # If we've still not yet seen the ">" prompt, hit enter and see if we
        # get one back
        if not self._seen_prompt:
            self.port.write('\r')
            check_response = True
            response += self._rx(checksum=False)
        # Because of the aforementioned BIOS crap, ignore everything but the
        # last line when checking for a response
        if check_response and not (response.endswith('LOGON\r') or
                response.endswith('INVALID COMMAND\r')):
            raise UnexpectedReply(
                'Expected LOGON or INVALID COMMAND, but got %s' % repr(response))
        logging.debug('TX: %s' % command)
        data = ','.join([command] + [str(arg) for arg in args]) + '\r'
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
        while '>\r' not in response:
            data = self.port.read().decode(ENCODING)
            if not data:
                raise ReceiveError('Failed to read any data before timeout')
            elif data == '\n':
                # Chuck away any LFs; these only appear in the BIOS output on
                # unit startup and mess up line splits later on
                continue
            elif data == '\r':
                logging.debug('RX: %s' % response.split('\r')[-1])
            response += data
        self._seen_prompt = True
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
        self._tx('GAPB')
        return self._rx()

    def _GPRB(self, bottle):
        """
        Sends a GPRB (Get PRessure Bottle) command to the OC110 and returns
        the data received.
        """
        self._tx('GPRB', bottle)
        return self._rx()

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
        self._tx('GMSK', bottle, head)
        return self._rx()

    @property
    def bottles(self):
        if self._bottles is None:
            data = self._GAPB()
            self._bottles = []
            bottle = ''
            # Split the response into individual bottles and their head line(s)
            for line in data.split('\r')[:-1]:
                if not line.startswith(','):
                    if bottle:
                        self._bottles.append(Bottle.from_string(bottle))
                    bottle = line + '\r'
                else:
                    bottle += line + '\r'
            if bottle:
                self._bottles.append(Bottle.from_string(bottle))
        return self._bottles

    def refresh(self):
        self._bottles = None


class DummySerial(object):
    """
    Emulates the serial port of an OxiTop OC110 Data Logger for testing.

    `baudrate` : the baud-rate to emulate, defaults to 9600
    """

    def __init__(self, port=None, baudrate=9600, bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
            timeout=None, xonxoff=False, rtscts=False, writeTimeout=None,
            dsrdtr=False, interCharTimeout=None):
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
        self._cts_high = None
        self._read_buf = []
        self._write_buf = ''
        self._opened = bool(self.port)
        #assert self.baudrate == 9600
        assert self.bytesize == serial.EIGHTBITS
        assert self.parity == serial.PARITY_NONE
        assert self.stopbits == serial.STOPBITS_ONE
        # On start-up, device sends some BIOS stuff, but as the port isn't
        # usually open at this point it typically gets lost/ignored. Is there
        # some decent way to emulate this?
        self._send('\0\r\n')
        self._send('BIOS OC Version 1.0\r\n')

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

    def flush(self):
        pass

    def flushInput(self):
        self._read_buf = []

    def flushOutput(self):
        self._write_buf = ''

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
        if level and self._cts_high is None:
            # Emulate the unit taking half a second to wake up and send the
            # LOGON message and prompt
            self._cts_high = time.time() + 0.5
            self._send('LOGON\r')
            self._send('>\r')
        else:
            self._cts_high = None

    def getCTS(self):
        return (self._cts_high is not None) and (time.time() > self._cts_high)

    def setDTR(self, level=True):
        raise NotImplementedError

    def getDSR(self):
        raise NotImplementedError

    def getRI(self):
        raise NotImplementedError

    def getCD(self):
        raise NotImplementedError

    def readinto(self, b):
        # XXX Should implement this from read()
        raise NotImplementedError

    def inWaiting(self):
        return sum(1 for (c, t) in self._read_buf if t < time.time())

    def read(self, size=1):
        if not self._opened:
            raise ValueError('port is closed')
        start = time.time()
        now = start
        result = ''
        while len(result) < size:
            if self._read_buf and self._read_buf[0][1] < now:
                result += self._read_buf[0][0]
                del self._read_buf[0]
            else:
                time.sleep(0.1)
            now = time.time()
            if self.timeout is not None and now > start + self.timeout:
                break
        assert len(result) <= size
        return result.encode('ASCII')

    def write(self, data):
        # Pause for the amount of time it would take to send data
        time.sleep(len(data) * 10 / self.baudrate)
        if not self._opened:
            raise ValueError('port is closed')
        self._write_buf += data.decode('ASCII')
        while '\r' in self._write_buf:
            command, self._write_buf = self._write_buf.split('\r', 1)
            if ',' in command:
                command = command.split(',')
                command, args = command[0], command[1:]
            else:
                args = []
            self._process(command, *args)
        return len(data)

    def _process(self, command, *args):
        if command == 'MAID':
            # MAnufacturer IDentifier; OC110 sends 'OC110'
            self._send('OC110\r')
        elif command == 'CLOC':
            # CLOse Connection; OC110 sends a return, a prompt, pauses, then
            # sends a NUL char, and finally the 'LOGON' prompt
            self._send('\r')
            self._send('>\r')
            self._cts_high = time.time() + 0.5
            self._send('\0')
            self._send('LOGON\r')
        elif command == 'GAPB':
            self._send('0,0,3,999,11022206,110222165455,110308165455,2,5,240,40,360,20160,510,432.0,0,10,2,1,56\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,999,11022207,110222165501,110308165501,2,5,240,40,360,20160,510,432.0,0,10,2,1,56\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,999,11022208,110222165523,110308165523,2,5,240,40,360,20160,510,432.0,0,10,2,1,56\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,999,11022209,110222165528,110308165528,2,5,240,40,360,20160,510,432.0,0,10,2,1,56\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,999,11022210,110222165548,110308165548,2,5,240,40,360,20160,510,432.0,0,10,2,1,56\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,1,12032301,120323173223,120420173223,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,1,12032302,120323173229,120420173229,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,1,12032303,120323173234,120420173234,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,1,12032304,120323173240,120420173240,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60121,150,\r')
            self._send('0,0,3,1,12032305,120323173318,120420173318,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60148,150,\r')
            self._send('0,0,3,1,12032306,120323173325,120420173325,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,1,12032307,120323173330,120420173330,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,1,12032308,120323173336,120420173336,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,1,12032309,120323173439,120420173439,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60134,150,\r')
            self._send('0,0,3,1,12032310,120323173445,120420173445,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60138,150,\r')
            self._send('0,0,3,1,12032311,120323173450,120420173450,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60131,150,\r')
            self._send('0,0,3,1,12042401,120424131232,120522131232,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60134,150,\r')
            self._send('0,0,3,1,12042402,120424131237,120522131237,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60138,150,\r')
            self._send('0,0,3,1,12042403,120424131243,120522131243,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60131,150,\r')
            self._send('0,0,3,1,12042404,120424131356,120522131356,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,1,12042405,120424131403,120522131403,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,1,12042406,120424131410,120522131410,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,1,12042407,120424131417,120522131417,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60121,150,\r')
            self._send('0,0,3,1,12042408,120424131455,120522131455,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60148,150,\r')
            self._send('0,0,3,1,12042409,120424131500,120522131500,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,1,12042410,120424131506,120522131506,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,1,12042411,120424131512,120522131512,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,1,12052301,120523152719,120620152719,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60134,150,\r')
            self._send('0,0,3,1,12052302,120523152726,120620152726,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60138,150,\r')
            self._send('0,0,3,1,12052303,120523152731,120620152731,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60131,150,\r')
            self._send('0,0,3,1,12052304,120523152814,120620152814,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,1,12052305,120523152820,120620152820,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,1,12052306,120523152826,120620152826,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,1,12052307,120523152832,120620152832,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60121,150,\r')
            self._send('0,0,3,1,12052308,120523152915,120620152915,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60148,150,\r')
            self._send('0,0,3,1,12052309,120523152921,120620152921,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,1,12052310,120523152927,120620152927,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,1,12052311,120523152933,120620152933,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,1,12062101,120621103126,120719103126,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60134,150,\r')
            self._send('0,0,3,1,12062102,120621103132,120719103132,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60138,150,\r')
            self._send('0,0,3,1,12062103,120621103138,120719103138,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60131,150,\r')
            self._send('0,0,3,1,12062104,120621103214,120719103214,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,1,12062105,120621103219,120719103219,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,1,12062106,120621103224,120719103224,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,1,12062107,120621103230,120719103230,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60121,150,\r')
            self._send('0,0,3,1,12062108,120621103259,120719103259,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60148,150,\r')
            self._send('0,0,3,1,12062109,120621103305,120719103305,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,1,12062110,120621103320,120719103320,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,1,12062111,120621103326,120719103326,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,1,12071901,120719151647,120816151647,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60134,150,\r')
            self._send('0,0,3,1,12071902,120719151703,120816151703,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60138,150,\r')
            self._send('0,0,3,1,12071903,120719151717,120816151717,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60131,150,\r')
            self._send('0,0,3,1,12071904,120719151820,120816151820,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,1,12071905,120719151836,120816151836,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,1,12071906,120719151915,120816151915,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,1,12071907,120719151931,120816151931,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60121,150,\r')
            self._send('0,0,3,1,12071908,120719152022,120816152022,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60148,150,\r')
            self._send('0,0,3,1,12071909,120719152028,120816152028,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,1,12071910,120719152033,120816152033,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,1,12071911,120719152040,120816152040,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,1,12082101,120821134723,120918134723,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60134,150,\r')
            self._send('0,0,3,1,12082102,120821134729,120918134729,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60138,150,\r')
            self._send('0,0,3,1,12082103,120821134735,120918134735,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60131,150,\r')
            self._send('0,0,3,1,12082104,120821134805,120918134805,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60148,150,\r')
            self._send('0,0,3,1,12082105,120821134816,120918134816,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,1,12082106,120821134823,120918134823,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,1,12082107,120821134829,120918134829,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,1,12082108,120821134857,120918134857,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,1,12082109,120821134903,120918134903,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,1,12082110,120821134909,120918134909,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,1,12082111,120821134915,120918134915,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60121,150,\r')
            self._send('0,0,3,1,12091801,120918145339,121016145339,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60134,150,\r')
            self._send('0,0,3,1,12091802,120918145345,121016145345,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60138,150,\r')
            self._send('0,0,3,1,12091803,120918145352,121016145352,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60131,150,\r')
            self._send('0,0,3,1,12091804,120918145433,121016145433,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60148,150,\r')
            self._send('0,0,3,1,12091805,120918145438,121016145438,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,1,12091806,120918145450,121016145450,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,1,12091807,120918145457,121016145457,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,1,12091808,120918145529,121016145529,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,1,12091809,120918145536,121016145536,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,1,12091810,120918145541,121016145541,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60121,150,\r')
            self._send('0,0,3,1,12091811,120918145548,121016145548,2,5,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,3,12103001,121030110410,121031110410,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,3,12103002,121030114331,121031114331,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,3,12103003,121030114339,121031114339,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,3,12110201,121102110637,121103110637,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,3,12110202,121102110721,121103110721,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,3,12110203,121102110744,121103110744,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,3,12110501,121105112507,121106112507,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,3,12110502,121105112629,121106112629,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,3,12110503,121105112638,121106112638,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,3,12110601,121106121024,121107121024,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,3,12110602,121106121032,121107121032,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,3,12110603,121106121045,121107121045,2,5,240,40,360,1440,510,432.0,0,2,2,1,4\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,3,12111201,121112154235,121210154235,1,1,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60134,150,\r')
            self._send('0,0,3,3,12111202,121112154241,121210154241,1,1,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60138,150,\r')
            self._send('0,0,3,3,12111203,121112154248,121210154248,1,1,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60131,150,\r')
            self._send('0,0,3,3,12111204,121112154256,121210154256,1,1,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60145,150,\r')
            self._send('0,0,3,3,12111205,121112154303,121210154303,1,1,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60109,150,\r')
            self._send('0,0,3,3,12111206,121112154311,121210154311,1,1,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60125,150,\r')
            self._send('0,0,3,3,12111207,121112154318,121210154318,1,1,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60121,150,\r')
            self._send('0,0,3,3,12111208,121112154325,121210154325,1,1,240,40,360,40320,510,432.0,0,10,2,1,308\r')
            self._send(',60148,150,\r')
            self._send('0,0,3,3,12111401,121114122222,121116122222,2,5,240,40,360,2880,510,432.0,0,4,2,1,8\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,3,12111402,121114122234,121116122234,2,5,240,40,360,2880,510,432.0,0,4,2,1,8\r')
            self._send(',60108,150,\r')
            self._send('0,0,3,3,12111403,121114122243,121116122243,2,5,240,40,360,2880,510,432.0,0,4,2,1,8\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,3,12111901,121119135242,121122135242,1,0,240,40,360,4320,510,432.0,0,6,2,1,12\r')
            self._send(',60050,150,\r')
            self._send('0,0,3,3,12111902,121119135255,121122135255,1,0,240,40,360,4320,510,432.0,0,6,2,1,12\r')
            self._send(',60133,150,\r')
            self._send('0,0,3,3,12111903,121119135304,121122135304,1,0,240,40,360,4320,510,432.0,0,6,2,1,12\r')
            self._send(',60108,150,\r')
            self._send(',0511361\r')
        else:
            self._send('INVALID COMMAND\r')
        self._send('>\r')

    def _send(self, response):
        # If the port isn't open, just chuck away anything that gets sent
        if self._opened:
            # Transmission settings are 8-N-1, so cps of transmission is
            # self.baudrate / 10. Delay between characters is the reciprocal of
            # this
            delay = 10 / self.baudrate
            if self._read_buf:
                when = self._read_buf[-1][1]
            else:
                when = time.time()
            for char in response:
                when += delay
                self._read_buf.append((char, when))


