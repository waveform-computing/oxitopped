=========
OxiTopped
=========

OxiTopped is a small suite of utilies for extracting data from an OxiTop data
logger via a serial (RS-232) port and dumping it to a specified file in various
formats. Options are provided for controlling the output, and for listing the
content of the device.

The suite was developed after reverse engineering the basic protocol of an
OxiTop OC110 pressure data logger. Our understanding of the protocol is
incomplete at best but sufficient for rudimentary data extraction. However, we
do not currently understand the data transfers that take place in certain
modes, like BOD. With more experimentation, we hope to add support for these
modes.


Homepage
========

The `OxiTopped homepage`_ has links to packages or instructions for all
supported platforms, and documentation.


License
=======

This file is part of oxitopped.

oxitopped is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

oxitopped is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
oxitopped.  If not, see <http://www.gnu.org/licenses/>.

.. _OxiTopped homepage: https://www.waveform.org.uk/oxitopped/

