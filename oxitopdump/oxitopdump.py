#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set et sw=4 sts=4:

# Copyright 2012 Dave Hughes.
#
# This file is part of oxitopdump.
#
# oxitopdump is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# oxitopdump is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# oxitopdump.  If not, see <http://www.gnu.org/licenses/>.

"""A simple application for listing data present on an OxiTop Data Logger

This application was developed after a quick reverse engineering of the basic
protocol of the OxiTop OC110 pressure data logger. Our understanding of the
protocol is incomplete at best but sufficient for data extraction.

"""

from __future__ import (
    unicode_literals,
    absolute_import,
    division,
    print_function,
    )

import os
import logging

from oxitopdump import Application


class DumpApplication(Application):
    """
    %prog [options] [bottle-serial]... filename

    This utility dumps the sample readings stored on a connected OxiTop Data
    Logger to files in CSV or Excel format. If bottle-serial values are
    specified, the details of those bottles and all heads attached to them will
    be exported, otherwise a list of all available bottles is exported.
    The bottle-serial values may include *, ?, and [] wildcards. The filename
    value may include references to bottle attributes like {bottle.serial} or
    {bottle.id}.
    """

    def main(self, options, args):
        super(DumpApplication, self).main(options, args)
        if args:
            pass
        else:
            for bottle in self.data_logger.bottles:
                print(bottle.serial)


main = DumpApplication()

