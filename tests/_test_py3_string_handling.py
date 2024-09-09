#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2011 Michael Vogt <mvo@ubuntu.com>
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

"""Regression test for a unicode decoding error in the status_details,
progress_download or error_properties attributes of the transaction,
see LP #724735.
"""

__author__ = "Michael Vogt <mvo@glatzor.de>"

import unittest

from aptkit.errors import TransactionFailed
from aptkit.test import AptKitTestCase


class TestUnicodeDecodingPy3(AptKitTestCase):

    def test_dbus_exception_lp846044(self):
        e = TransactionFailed("foo", "bar")
        e.details = "ä"
        self.assertEqual(str(e), "Transaction failed: None\nä")


if __name__ == "__main__":
    unittest.main()

# vim: ts=4 et sts=4
