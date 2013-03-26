.. _oxitopemu:

=========
oxitopemu
=========

The oxitopemu utility emulates an `OxiTop OC110`_ device, or at least the
serial port data retrieval portion anyway. This utility is of niche interest;
it is intended for developers wishing to work on OxiTopped without having to
have an actual OC110 to hand.


Synopsis
========

::

  $ oxitopemu [options] bottles-xml


Description
===========

.. program:: oxitopemu

.. option:: --version

   show program's version number and exit

.. option:: -h, --help

   show this help message and exit

.. option:: -q, --quiet

   produce less console output

.. option:: -v, --verbose

   produce more console output

.. option:: -l LOGFILE, --log-file=LOGFILE

   log messages to the specified file

.. option:: -P, --pdb

   run under PDB (debug mode)

.. option:: -p PORT, --port=PORT

   specify the port which the OxiTop Data Logger is connected to. This will be
   something like /dev/ttyUSB0 on Linux or COM1 on Windows. Default:
   /dev/ttyUSB0

.. option:: -t TIMEOUT, --timeout=TIMEOUT

   specify the number of seconds to wait for data from the serial port.
   Default: 3

.. option:: -d, --daemon

   if specified, start the emulator as a background daemon


Usage and Notes
===============

Simply install the emulator on a small machine with a serial port (personally I
use a `RaspberryPi`_ with a `USB to Serial`_ adapter), then use a `null-modem`_
between the machine running the client and the machine running the emulator.  A
default set of bottle definitions in XML format is included in the package as
``example.xml`` under the main package's installation directory.

If you have the python-daemon package installed (it's included in the
dependencies of the Linux packages, and is bundled with the Windows installer)
you can run the emulator in daemon mode.

The main purpose of the emulator is to test the applications in a setting with
a "real" serial interface. For testing command compatibility, there is no need
to use `oxitopemu`_ directly; the emulation code is used internally by each of
the clients when the ``TEST`` port is specified. In this case, an emulated
null-modem is used to connect the emulation code to the client.


.. _null-modem: http://www.amazon.co.uk/StarTech-RS232-Serial-Modem-Adapter/dp/B000DZH4V0/ref=pd_sim_ce_5
.. _OxiTop OC110: http://www.wtw.de/en/products/lab/bodrespiration/depletionrespiration-with-oxitopr-control-oc-110.html
.. _RaspberryPi: http://www.raspberrypi.org/
.. _USB to Serial: http://www.amazon.co.uk/Plugable-Adapter-Prolific-PL2303HX-Chipset/dp/B00425S1H8/ref=cm_cr_pr_product_top

