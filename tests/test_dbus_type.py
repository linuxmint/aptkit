#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test index handling."""

from collections import namedtuple
import os
import re
import sys
import unittest

import dbus
from gi.repository import GLib

from aptkit.worker import aptworker
from aptkit import core
from aptkit import enums
from aptkit import test

REGEX_SIG = "([ibxsdt])|(a{[ibxsdt]+?})|(a[ixbsdt]+?)|(\([ibxsdt]+?\))"
REGEX_IFACE = r"\n(org\.debian\.apt[a-z\.]*) --- "
REGEX_ATTRIB = (r"\n\.\.\s+attribute::\s+(?P<name>[a-zA-Z]+)\s+:\s+"
                "(?P<sig>[a-z\(\)\{\}]+)")

# Setup the DBus main loop
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

DOC_PATH = os.path.join(test.get_tests_dir(), "../doc")


class DBusTypeTest(test.AptKitTestCase):

    """Make sure that the specified types are returned over D-Bus."""

    def setUp(self):
        # Extract the property type specification from the documentation
        self.ifaces = {}
        with open(os.path.join(DOC_PATH, "source/dbus.rst")) as rst_file:
            docu = rst_file.read()
        doc = ""
        iface = ""
        for match in re.split(REGEX_IFACE, docu, re.MULTILINE):
            if match.startswith("org.debian.apt"):
                iface = match
                self.ifaces[iface] = {}
                doc = ""
            else:
                doc = match
            if doc and iface:
                for match_attrib in re.finditer(REGEX_ATTRIB, doc):
                    name = match_attrib.group("name")
                    sig = match_attrib.group("sig")
                    self.ifaces[iface][name] = sig
        self.start_dbus_daemon()
        self.dbus = dbus.bus.BusConnection(self.dbus_address)
        self.loop = GLib.MainLoop()
        self.error = None

    def _on_property_changed(self, name, value, iface):
        if name == "Progress" and value == 100:
            self.loop.quit()
        try:
            self._check_property_type(iface, name, value)
        except:
            self.loop.quit()
            raise

    def _check_property_type(self, iface, name, value, signature=None):
        if signature is None:
            signature = self.ifaces[iface][name]
        if isinstance(value, dbus.String):
            self.assertEqual(signature, "s",
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        elif isinstance(value, dbus.String):
            self.assertEqual(signature, "s",
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        elif isinstance(value, dbus.Int32):
            self.assertEqual(signature, "i",
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        elif isinstance(value, dbus.Int64):
            self.assertEqual(signature, "x",
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        elif isinstance(value, dbus.UInt64):
            self.assertEqual(signature, "t",
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        elif isinstance(value, dbus.Double):
            self.assertEqual(signature, "d",
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        elif isinstance(value, dbus.Boolean):
            self.assertEqual(signature, "b",
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        elif isinstance(value, dbus.Dictionary):
            self.assertEqual(signature, "a{%s}" % value.signature,
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        elif isinstance(value, dbus.Struct):
            if value.signature:
                self.assertEqual(signature, "s(%s)" % value.signature,
                                 "Property %s on %s doesnt' comply with the "
                                 "spec: %s" % (name, iface, value))
            else:
                # The dbus proxy doesn't set the signature property
                for val, sig in map(lambda x, y: (x, y), value,
                                    ["".join(matches) for matches in
                                     re.findall(REGEX_SIG, signature[1:-1])]):
                    self._check_property_type(iface, name, val, sig)
        elif isinstance(value, dbus.Array):
            self.assertEqual(signature, "a%s" % value.signature,
                             "Property %s on %s doesnt' comply with the "
                             "spec: %s" % (name, iface, value))
        else:
            raise Exception("Unkown type %s for property %s of %s" %
                            (type(value), name, iface))

    def _error_cb(self, error):
        """Errback of the GetAll call."""
        self.loop.quit()
        raise error

    def _get_all_cb(self, iface, props):
        """Callback of the GetAll call."""
        try:
            for name, value in props.items():
                self._check_property_type(iface, name, value)
        except Exception as error:
            self.error = error
            raise
        finally:
            self.loop.quit()

    @unittest.skip("Requires to be convert to a C based test client")
    def test_transaction_properties(self):
        """Test object properties."""
        trans = core.Transaction(None, enums.ROLE_REMOVE_PACKAGES, None,
                                 os.getpid(), os.getuid(), sys.argv[0],
                                 "org.debian.apt.test", bus=self.dbus)
        proxy = self.dbus.get_object(core.APTKIT_DBUS_INTERFACE,
                                     trans.tid)
        iface = core.APTKIT_TRANSACTION_DBUS_INTERFACE
        proxy.GetAll(iface,
                     reply_handler=lambda x: self._get_all_cb(iface, x),
                     error_handler=self._error_cb,
                     dbus_interface=dbus.PROPERTIES_IFACE)
        self.loop.run()
        self.assertEqual(self.error, None, self.error)

    @unittest.skip("Requires to be convert to a C based test client")
    def test_transaction_signals(self):
        """Test signal emittion."""
        trans = core.Transaction(None, enums.ROLE_COMMIT_PACKAGES, None,
                                 os.getpid(), os.getuid(), sys.argv[0],
                                 "org.debian.apt.test", bus=self.dbus,
                                 packages=[["silly-base"], [], [], [], [], []])
        proxy = self.dbus.get_object("org.debian.apt", trans.tid)
        proxy.connect_to_signal("PropertyChanged",
                                self._on_property_changed,
                                dbus_interface="org.debian.apt.transaction",
                                interface_keyword="iface")
        chroot = test.Chroot()
        self.addCleanup(chroot.remove)
        chroot.setup()
        chroot.add_test_repository()
        apt_worker = aptworker.AptWorker(load_plugins=False,
                                         chroot=chroot.path)
        apt_worker.run(trans)
        self.loop.run()
        self.assertEqual(self.error, None)

    @unittest.skip("Requires to be convert to a C based test client")
    def test_aptkit_properties(self):
        """Test aptkit properties."""
        Options = namedtuple("Options", "dummy")
        opt = Options(True)
        self.daemon = core.AptKit(opt, bus=self.dbus)

        proxy = self.dbus.get_object(core.APTKIT_DBUS_SERVICE,
                                     core.APTKIT_DBUS_PATH)
        iface = core.APTKIT_DBUS_INTERFACE
        proxy.GetAll(iface,
                     reply_handler=lambda x: self._get_all_cb(iface, x),
                     error_handler=self._error_cb,
                     dbus_interface=dbus.PROPERTIES_IFACE)
        self.loop.run()
        self.assertEqual(self.error, None)


if __name__ == "__main__":
    unittest.main()

# vim: ts=4 et sts=4
