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

.. option:: -H, --header

   if specified, a header row will be written in the output file

.. option:: -R, --row-colors

   if specified, alternate row coloring will be used in the output file (.xls
   only)

.. option:: -C DELIMITER, --column-delimiter=DELIMITER

   specifies the column delimiter in the output file.  Defaults to ``,`` (.csv
   only)

.. option:: -L LINETERMINATOR, --line-terminator=LINETERMINATOR

   specifies the line terminator in the output file.  Defaults to ``dos`` (.csv
   only)

.. option:: -Q QUOTECHAR, --quote-char=QUOTECHAR

   specifies the character used for quoting strings in the output file.
   Defaults to ``"`` (.csv only)

.. option:: -U QUOTING, --quoting=QUOTING

   specifies the quoting behaviour used in the output file. Defaults to minimal
   (.csv only). Can be none, all, minimal, or nonnumeric

.. option:: -T TIMESTAMP_FORMAT, --timestamp-format=TIMESTAMP_FORMAT

   specifies the formatting of timestamps in the output file. Defaults to
   ``%Y-%m-%d %H:%M:%S`` (.csv only)


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
    $ cat readings.csv
    0,2012-03-23 17:32:23,0:00:00,0.0,0.0
    1,2012-03-23 19:24:23,1:52:00,-12.0,-5.0
    2,2012-03-23 21:16:23,3:44:00,-13.0,-5.0
    3,2012-03-23 23:08:23,5:36:00,-13.0,-5.0
    4,2012-03-24 01:00:23,7:28:00,-13.0,-5.0
    ...
    357,2012-04-20 11:56:23,"27 days, 18:24:00",-16.0,-8.0
    358,2012-04-20 13:48:23,"27 days, 20:16:00",-17.0,-8.0
    359,2012-04-20 15:40:23,"27 days, 22:08:00",-17.0,-9.0
    360,2012-04-20 17:32:23,"28 days, 0:00:00",-16.0,-8.0

If you specify multiple *bottle-serials* or if you specify a *bottle-serial*
with wildcards which matches multiple bottles, you will need to specify a
filename containing a substitution template like ``{bottle.serial}`` so that
each bottle is output to a unique file. For example::

    $ oxitopdump -p /dev/ttyUSB0 12* readings_{bottle.serial}.xls
    $ ls *.xls
    readings_120323-01.xls  readings_121119-03.xls

Various options are provided for customizing the output of the formats
available.  For example, to include a header row and force space separation::

    $ oxitopdump -p /dev/ttyUSB0 -H -D " " 11* test.csv
    $ head test.csv
    No. Timestamp Offset "Head 60108"
    0 "2011-02-22 16:54:55" 0:00:00 0.0
    1 "2011-02-22 17:50:55" 0:56:00 -5.0
    2 "2011-02-22 18:46:55" 1:52:00 -5.0
    3 "2011-02-22 19:42:55" 2:48:00 -5.0
    4 "2011-02-22 20:38:55" 3:44:00 -5.0
    5 "2011-02-22 21:34:55" 4:40:00 -5.0
    6 "2011-02-22 22:30:55" 5:36:00 -6.0
    7 "2011-02-22 23:26:55" 6:32:00 -5.0
    8 "2011-02-23 00:22:55" 7:28:00 -5.0

