==========
oxitopdump
==========

Oxitopdump is a small suite of utilies for extracting data from an OxiTop data
logger via a serial (RS-232) port and dumping it to a specified file in various
formats. Options are provided for controlling the output, and for listing the
content of the device.

The suite was developed after reverse engineering the basic protocol of an
OxiTop OC110 pressure data logger. Our understanding of the protocol is
incomplete at best but sufficient for rudimentary data extraction. However, we
do not currently understand the data transfers that take place in certain
modes, like BOD. With more experimentation, we hope to add support for these
modes.


Installation
============

The `project homepage <http://www.waveform.org.uk/oxitopdump/>`_ has links to
packages or instructions for all supported platforms.


Instructions
============

Firstly, connect the OxiTop OC110 to the serial port on your computer. You will
need to know the name of this port for your particular OS. On Linux this will
be something like ``/dev/ttyUSB0``. On Windows, something like ``COM1``.

Switch on the OxiTop OC110 by pressing the red On/Off key at the bottom right
and wait for the screen to display the list of results. Then, use the
oxitoplist utility to list the set of pressure bottle results currently stored
on the device.  To obtain details of a specific result, specify the bottle
serial number on the oxitoplist command line.  The oxitopdump utility can be
used to obtain the same data in a variety of formats (currently CSV and Excel).

Finally, the oxitopview utility is a GUI interface for performing these same
listing and extraction functions. The oxitopview utility will optionally use
matplotlib (if it is installed) to graph the pressure results from bottles.


License
=======

This file is part of oxitopdump.

oxitopdump is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

oxitopdump is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
oxitopdump.  If not, see <http://www.gnu.org/licenses/>.

