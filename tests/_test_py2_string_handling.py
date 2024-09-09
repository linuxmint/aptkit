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

import os
import sys
import unittest

import dbus
from dbus.lowlevel import ErrorMessage, Message

from aptkit.core import Transaction
from aptkit.errors import TransactionFailed
from aptkit.test import AptKitTestCase, Chroot


class TestUnicodeDecoding(AptKitTestCase):

    """Test the workaround."""

    def setUp(self):
        self.chroot = Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        self.start_dbus_daemon()
        self.dbus = dbus.bus.BusConnection(self.dbus_address)
        self.trans = Transaction(None, "role-test", None,
                                 os.getpid(), os.getuid(), os.getgid(),
                                 sys.argv[0],
                                 "org.debian.aptkit.test", bus=self.dbus)

    def test(self):
        # ensure we don't crash regardless if str or unicode is passed here
        self.trans.status_details = "äää"
        self.trans.status_details = u"äää"

        self.trans.progress_download = ("äö", "ß", "üöä", 1L, 2L, "ö")
        self.trans.progress_download = (u"äö", u"ß", u"üöä", 1L, 2L, u"ö")

        self.trans.error = TransactionFailed("ERROR_TEST", "Mixed ä %s", u"öä")
        self.trans.error = TransactionFailed("ERROR_TEST", u"Mixed ü %s", "öä")
        self.trans.error = TransactionFailed("ERROR_TEST", "Str ä %s", "öä")
        self.trans.error = TransactionFailed("ERROR_TEST", u"Uni ä %s", u"öä")

    def test_dbus_exception(self):
        """This tests simulates the steps taken by the DBus bindings to
        send an error reply, see LP# 761386"""
        # The original error message that we get from python-apt
        orig = "E:Die Paketliste oder die Statusdatei konnte nicht " \
               "eingelesen oder ge\xc3\xb6ffnet werden."
        for msg in [u"E:Die Paketliste oder die Statusdatei konnte nicht "
                    u"eingelesen oder geöffnet werden.",
                    "E:Die Paketliste oder die Statusdatei konnte nicht "
                    "eingelesen oder geöffnet werden.", orig]:
            # Create a simple DBus exception
            error = TransactionFailed("ERROR_TEST", msg)

            # Taken from dbus.service._method_reply_error()
            name = error.get_dbus_name()
            content = error.get_dbus_message()
            self.assertEqual(orig, content[12:])
            # The constructor of the ErrorMessage fails since we only use
            # a fake Message
            self.assertRaises(MemoryError, ErrorMessage, Message(), name,
                              content)

    def test_dbus_exception_lp846044(self):
        e = TransactionFailed("foo", "bar")
        e.details = u"ä"
        foo = unicode(e)
        self.assertEqual(foo, u"Transaction failed: None\nä")
        foo = str(e)
        self.assertEqual(foo, u"Transaction failed: None\nä".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()

# vim: ts=4 et sts=4
