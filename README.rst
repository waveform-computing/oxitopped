==========
oxitopdump
==========

oxitopdump is a small utility for extracting data from an OxiTop OC110 data
logger via a serial (RS-232) port and dumping it to a specified file in CSV
format. Various options are provided for controlling output and specified the
serial port that the data logger is connected to.


Installation
============

oxitopdump requires Python 2.6 or above (3.x currently untested), and pyserial
(unsurprisingly). It has been tested on Ubuntu 12.04 and Windows XP, but should
work on other versions and Mac OS X provided all dependencies are met. After
installing Python on your system, you can install oxitopdump from the PyPI
repository with the following command::

   $ easy_install oxitopdump

Or, if you've got Python distribute installed::

   $ pip install oxitopdump

Either of these commands should pull in all necessary installation dependencies
and install the utility.


Instructions
============

Firstly, connect the OxiTop OC110 to the serial port on your computer. You will
need to know the name of this port for your particular OS. On Linux this will
be something like ``/dev/ttyUSB0``. On Windows, something like ``COM1``.

Switch on the OxiTop OC110 by pressing the red On/Off key at the bottom right
and wait for the screen to display the list of results.

From the command line issue a command like the following (substituting as
necessary for the serial port and output filename)::

    $ oxitopdump --port=/dev/ttyUSB0 output.csv

After starting the above command, quickly press the Up or Down key on the
OxiTop OC110 and you should see "V24-Modus" appear on the display. If you
aren't quick enough, the oxitopdump command may timeout, but this is okay. If
this happens simply restart the command while "V24-Modus" is still displayed
and the data dump should start.


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

