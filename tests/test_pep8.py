#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Make sure that the code conforms the PEP8 conventions."""
# Copyright (C) 2012 Sebastian Heinlein <devel@glatzor.de>
#
# Licensed under the GNU General Public License Version 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# Licensed under the GNU General Public License Version 2

__author__ = "Sebastian Heinlein <devel@glatzor.de>"

import subprocess
import unittest


@unittest.skip("Does not work")
class AptDaemonPep8TestCase(unittest.TestCase):

    def test(self):
        """Check if the source code matches the PEP8 style conventions."""
        subprocess.check_call([
            "pep8", "--statistics", "--show-source",
            "--show-pep8", "--exclude",
            "pkenums.py,aptdaemon,tests,debian,doc,.pc,gtk3-demo.py,setup.py",
            "--ignore=E402"])


if __name__ == "__main__":
    unittest.main()
