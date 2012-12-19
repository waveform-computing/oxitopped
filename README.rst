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

oxitopdump requires Python 2.6 or above (3.x currently untested), and pyserial
(unsurprisingly). Additional optional dependencies exist if you wish to use
Excel output (the xlwt package) or the GUI interface (the pyqt4, numpy, and
matplotlib packages). It has been tested on Ubuntu 12.04 and Windows XP, but
should work on other versions and Mac OS X provided all dependencies are met.
After installing Python on your system, you can install oxitopdump from the
PyPI repository with the following command::

   $ easy_install oxitopdump

Or, if you've got Python distribute installed::

   $ pip install oxitopdump

Either of these commands should pull in all necessary installation dependencies
and install the suite.


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

