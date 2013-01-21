==========
oxitopdump
==========

This utility dumps the sample readings stored on a connected OxiTop Data Logger
to files in CSV or Excel format. If bottle-serial values are specified, the
details of those bottles and all heads attached to them will be exported,
otherwise a list of all available bottles is exported. The bottle-serial values
may include \*, ?, and [] wildcards. The filename value may include references
to bottle attributes like {bottle.serial} or {bottle.id}.

Synopsis
========

::

  $ oxitopdump [options] [bottle-serial]... filename

Description
===========

.. program:: oxitopdump

.. option::  --version

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
   something like ``/dev/ttyUSB0`` on Linux or COM1 on Windows

.. option:: -a, --absolute

   if specified, export absolute pressure values instead of deltas against the
   first value

.. option:: -m POINTS, --moving-average=POINTS

   if specified, export a moving average over the specified number of points
   instead of actual readings

Examples
========

When `oxitopdump` is invoked without specifying a *bottle-serial* the list of
bottles will be exported to the specified filename. Typically you will want
to use `oxitoplist` to discover the content of the connected device before
exporting the readings for a specific bottle like so::

    $ oxitoplist -p /dev/ttyUSB0
    Serial    ID  Started    Finished   Complete Mode         Heads
    --------- --- ---------- ---------- -------- ------------ -----
    110222-06 999 2011-02-22 2011-03-08 Yes      Pressure 14d 1
    121119-03 3   2012-11-19 2012-11-22 Yes      Pressure 3d  1
    120323-01 1   2012-03-23 2012-04-20 Yes      Pressure 28d 2

    3 results returned
    $ oxitopdump -p /dev/ttyUSB0 120323-01 readings.csv

