========
Welcome!
========

`OxiTopped`_ is a small suite of utilies for extracting data from an `OxiTop
OC110`_ data logger via a serial (RS-232) port and dumping it to a specified
file in various formats. Options are provided for controlling the output, and
for listing the content of the device.


Disclaimer
==========

OxiTopped is not affiliated with, or endorsed by `WTW GmbH`_ in any way. This
is a personal project to provide an interface to the `OxiTop OC110`_ on
alternate platforms.


.. warning::

   OxiTopped is currently incomplete. My understanding of the serial protocol
   used to communicate with the device is probably sufficient to retrieve data
   from pressure mode runs (including manual measurements, although this is not
   currently implemented), but retrieval of data from BOD mode runs should be
   considered experimental at best.


Contents
========

.. toctree::
   :maxdepth: 1

   install
   oxitoplist
   oxitopdump
   oxitopview
   oxitopemu
   protocol
   license


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
* :ref:`modindex`

.. _OxiTopped: https://www.waveform.org.uk/oxitopped/
.. _OxiTop OC110: http://www.wtw.de/en/products/lab/bodrespiration/depletionrespiration-with-oxitopr-control-oc-110.html
.. _WTW GmbH: http://www.wtw.de/en/home.html

