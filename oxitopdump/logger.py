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
Defines the interfaces for gathering data from an OC110, and an OC110 emulator.

This module defines a `DataLogger` class which provides an interface to the
OC110 serial port. For testing purposes a "fake OC110" can be found in the
`DummyLogger` class. This can be connected to an application with real serial
ports or with instances of the NullModem class in the associated nullmodem
module.
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import time
import logging
from datetime import datetime, timedelta
from threading import Thread

import serial

from oxitopdump.bottles import Bottle, BottleHead, ENCODING


class LoggerError(Exception):
    """
    Base class for errors related to the data-logger
    """


class SendError(LoggerError):
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


class ReceiveError(LoggerError):
    """
    Exception raise due to a reception error
    """


class TimeoutError(ReceiveError):
    """
    Exception raised when we get no data back before the port times out
    """


class UnexpectedReply(ReceiveError):
    """
    Exception raised when the data logger sends back an unexpected reply
    """


class ChecksumMismatch(ReceiveError):
    """
    Exception raised when a check-sum doesn't match the data sent
    """


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
        self.id = self._MAID().rstrip('\r')
        if self.id != 'OC110':
            raise UnexpectedReply(
                'Unexpected manufacturer ID: %s' % self.id)

    def _tx(self, command, *args):
        """
        Sends a command (and optionally arguments) to the OC110. The command
        should not include the line terminator and the arguments should not
        include comma separators; this method takes care of command formatting.

        `command` : The command to send
        """
        response = ''
        if not self.port.isOpen():
            self.port.open()
        if not self._seen_prompt:
            self.port.flushInput()
            # If we've not seen the ">" prompt yet, prod the unit repeatedly
            # until we see it or hit the retries limit
            for i in range(self.retries):
                logging.debug('DTE: no prompt seen, prodding unit')
                self.port.write('\r\n')
                try:
                    response += self._rx(checksum=False)
                except TimeoutError:
                    continue
                break
            if not self._seen_prompt:
                raise TimeoutError(
                    'Unit did not respond within %d retries' % self.retries)
            # Because of BIOS crap, ignore everything but the last line when
            # checking for a response
            if not (response.endswith('LOGON\r') or
                    response.endswith('INVALID COMMAND\r')):
                raise UnexpectedReply(
                    'Expected LOGON or INVALID COMMAND, but got %s' % response)
        data = ','.join([command] + [str(arg) for arg in args]) + '\r\n'
        logging.debug('DTE TX: %s' % data.rstrip('\r\n'))
        written = self.port.write(data.encode(ENCODING))
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
                    raise TimeoutError('Failed to read any data before timeout')
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
        self._rx(checksum=False)
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
        if '-' in bottle:
            bottle, id = bottle.split('-', 1)
            bottle = ''.join((bottle, id))
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

    def close(self):
        """
        Tell the logger to close its connection and reset.
        """
        if self.port.isOpen():
            self._CLOC()
            self.port.close()


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
        self.port = port
        self._sent_prompt = False
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
            pressure_limit=150,
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
            pressure_limit=150,
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
            pressure_limit=150,
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
            pressure_limit=150,
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
        self.port.write('\r\n')
        self.port.write('BIOS OC Version 1.0\r\n')
        while not self.terminated:
            buf += self.port.read().decode('ASCII')
            while '\r\n' in buf:
                command, buf = buf.split('\r\n', 1)
                logging.debug('DCE RX: %s' % command)
                if ',' in command:
                    command = command.split(',')
                    command, args = command[0], command[1:]
                else:
                    args = []
                self.handle(command, *args)
        self.port.close()

    def send(self, data, checksum=False):
        """
        Sends data over the serial port with an optional checksum suffix. The
        method ensures the port is open, RTS is set, and CTS is received before
        beginning transmission.
        """
        if not self.port.isOpen():
            self.port.open()
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
            # CLOse Connection; OC110 sends a return, a prompt, closes the
            # connection, then re-opens it, and finally sends the 'LOGON'
            # prompt
            self.send('\r')
            self.send('>\r')
            self.port.close()
            self._sent_prompt = False
            # Emulate the unit taking a half second to restart
            time.sleep(0.5)
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
            # XXX Implement this properly - it returns the "manual" readings
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
        elif not self._sent_prompt:
            self.send('LOGON\r')
            self._sent_prompt = True
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



