============
Installation
============

oxitopdump is distributed in several formats. The following sections detail
installation on a variety of platforms.


Pre-requisites
==============

oxitopdump depends primarily on `pyserial <http://pyserial.sourceforge.net/>`_.
If you wish to use the GUI you will also need `PyQt4
<http://www.riverbankcomputing.com/software/pyqt/download>`_ installed.

Additional optional dependencies are:

 * `xlwt <http://pypi.python.org/pypi/xlwt>`_ - required for Excel writing support

 * `maptlotlib <http://matplotlib.org>`_ - required for graphing support


Ubuntu Linux
============

For Ubuntu Linux it is simplest to install from the PPA as follows::

    $ sudo add-apt-repository ppa://waveform/ppa
    $ sudo apt-get update
    $ sudo apt-get install oxitopdump

Development
-----------

If you wish to develop oxitopdump, you can install the pre-requisites,
construct a virtualenv sandbox, and check out the source code from subversion
with the following command lines::

   # Install the pre-requisites
   $ sudo apt-get install python-matplotlib python-xlwt python-qt4 python-virtualenv python-sphinx make git

   # Construct and activate a sandbox with access to the packages we just
   # installed
   $ virtualenv --system-site-packages sandbox
   $ source sandbox/bin/activate

   # Check out the source code and install it in the sandbox for development and testing
   $ git clone https://github.com/waveform80/oxitopdump.git
   $ cd oxitopdump
   $ make develop


Microsoft Windows
=================

On Windows, it is probably simplest to install one of the pre-built Python
distributions that includes matplotlib like the `Enthought Python Distribution
<http://enthought.com/products/epd.php>`_ or `Python (x,y)
<http://code.google.com/p/pythonxy/>`_ (both of these include matplotlib and
PyQt4), then start a command window from within the environment and use the
following command::

  $ pip install oxitopdump


Apple Mac OS X
==============

XXX To be written


Other Platforms
===============

If your platform is *not* covered by one of the sections above, oxitopdump is
available from PyPI and can therefore be installed with the distribute ``pip``
tool::

   $ pip install oxitopdump

Theoretically this should install pre-requisites, but certain things like PyQt4
require installation steps not supported by the pip installer and might
therefore require manual installation steps beforehand.


