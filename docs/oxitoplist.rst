==========
oxitoplist
==========

This utility lists the sample results stored on a connected OxiTop Data
Logger. If bottle-serial values are specified, the details of those bottles
and all heads attached to them will be displayed, otherwise a list of all
available bottle serials provided. The bottle-serial values may include \*,
?, and [] wildcards.

Synopsis
========

::

  $ oxitoplist [options] [bottle-serial]...

Description
===========

.. program:: oxitoplist

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

.. option:: -D, --debug

   enables debug mode (runs under PDB)

.. option:: -p PORT, --port=PORT

   specify the port which the OxiTop Data Logger is connected to. This will be
   something like /dev/ttyUSB0 on Linux or COM1 on Windows

.. option:: -r, --readings

   if specified, output readings for each head after displaying bottle details

.. option:: -a, --absolute

   if specified with --readings, output absolute pressure values instead of
   deltas against the first value

.. option:: -m POINTS, --moving-average=POINTS

   if specified with --readings, output a moving average over the specified
   number of points instead of actual readings

Examples
========

Basic Usage
-----------

The most basic usage of oxitoplist is to dump a list of the bottles stored on
the connected device::

    $ oxitoplist -p /dev/ttyUSB0
    Serial    ID  Started    Finished   Complete Mode         Heads
    --------- --- ---------- ---------- -------- ------------ -----
    110222-06 999 2011-02-22 2011-03-08 Yes      Pressure 14d 1
    121119-03 3   2012-11-19 2012-11-22 Yes      Pressure 3d  1
    120323-01 1   2012-03-23 2012-04-20 Yes      Pressure 28d 2

    3 results returned

If one or more bottle-serial numbers are listed on the command line (which may
include wildcards), the details of the bottles listed are output instead::

    $ oxitoplist -p /dev/ttyUSB0 12*

    Serial                 121119-03
    ID                     3
    Started                2012-11-19 13:53:04
    Finished               2012-11-19 13:53:04
    Readings Interval      0:12:00
    Completed              Yes
    Mode                   Pressure 3d
    Bottle Volume          510.0ml
    Sample Volume          432.0ml
    Dilution               1+0
    Desired no. of Values  360
    Actual no. of Values   0
    Heads                  1

    Serial                 120323-01
    ID                     1
    Started                2012-03-23 17:32:23
    Finished               2012-03-23 17:32:23
    Readings Interval      1:52:00
    Completed              Yes
    Mode                   Pressure 28d
    Bottle Volume          510.0ml
    Sample Volume          432.0ml
    Dilution               1+0
    Desired no. of Values  360
    Actual no. of Values   361
    Heads                  2

