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
Monkey patches used by oxitopped.
"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import os
import sys

import serial
import serial.tools.list_ports


# The following is derived from a patch [1] which works around (but doesn't
# really fix) a bug [2] on the pyserial trackers. Specifically, pyserial
# *should* look at the bus and device number for a USB-based serial device, but
# instead parses the path, extracting the bus and *port* number (which often
# matches the device number but sometimes doesn't). To compound matters, if it
# fails to query the serial device (because of the wrong device number), it
# then tries to access an undefined variable name, raising a NameError
# exception.
#
# [1] http://sourceforge.net/tracker/?func=detail&aid=3462364&group_id=46487&atid=446304
# [2] http://sourceforge.net/tracker/?func=detail&aid=3554871&group_id=46487&atid=446302

if float(serial.VERSION) < 2.7 and sys.platform.lower()[:5] == 'linux':
    import serial.tools.list_ports_posix
    from serial.tools.list_ports_posix import re_group, popen

    def usb_lsusb_string(sysfs_path):
        base = os.path.basename(os.path.realpath(sysfs_path))
        bus, dev = base.split('-')
        try:
            desc = popen(['lsusb', '-v', '-s', '%s:%s' % (bus, dev)])
            # descriptions from device
            iManufacturer = re_group('iManufacturer\s+\w+ (.+)', desc)
            iProduct = re_group('iProduct\s+\w+ (.+)', desc)
            iSerial = re_group('iSerial\s+\w+ (.+)', desc) or ''
            # descriptions from kernel
            idVendor = re_group('idVendor\s+0x\w+ (.+)', desc)
            idProduct = re_group('idProduct\s+0x\w+ (.+)', desc)
            # create descriptions. prefer text from device, fall back to the others
            return '%s %s %s' % (iManufacturer or idVendor, iProduct or idProduct, iSerial)
        except IOError:
            return base

    serial.tools.list_ports_posix.usb_lsusb_string = usb_lsusb_string
