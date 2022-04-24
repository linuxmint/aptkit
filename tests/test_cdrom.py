#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the client module."""

import logging
import time
import unittest

import defer
import dbus

import aptdaemon.client
import aptdaemon.loop
import aptdaemon.enums

import aptdaemon.test

DEBUG = True


class CDROMTestCase(aptdaemon.test.AptDaemonTestCase):

    """Test the installation from removable media, e.g. CDROMs."""

    def setUp(self):
        """Setup a chroot, run the aptdaemon and a fake PolicyKit daemon."""
        # Setup chroot
        self.chroot = aptdaemon.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        self.chroot.add_trusted_key()
        self.chroot.add_cdrom_repository()
        # Start aptdaemon with the chroot on the session bus
        self.start_dbus_daemon()
        self.bus = dbus.bus.BusConnection(self.dbus_address)
        self.start_session_aptd(self.chroot.path)
        # Start the fake PolikcyKit daemon
        self.start_fake_polkitd()
        time.sleep(1)
        self.called = False

    @defer.inline_callbacks
    def _on_medium_required_cancel(self, trans, medium, mount_point):
        yield trans.cancel()

    @defer.inline_callbacks
    def _on_medium_required(self, trans, medium, mount_point):
        if self.called:
            # Abort if we get asked twice for the cdrom
            yield trans.cancel()
        self.chroot.mount_cdrom()
        self.called = True
        yield trans.provide_medium(medium)

    def _on_finished(self, trans, exit):
        """Callback to stop the mainloop after a transaction is done."""
        aptdaemon.loop.mainloop.quit()

    def test(self):
        """Test changing media."""
        @defer.inline_callbacks
        def run():
            self.client = aptdaemon.client.AptClient(self.bus)
            trans = yield self.client.install_packages(["silly-depend-base"])
            trans.connect("finished", self._on_finished)
            trans.connect("medium-required", self._on_medium_required)
            yield trans.run()
            defer.return_value(trans)
        deferred = run()
        aptdaemon.loop.mainloop.run()
        self.assertEqual(deferred.result.exit, aptdaemon.enums.EXIT_SUCCESS)

    def test_cancel(self):
        """Test cancelling a required medium request."""
        @defer.inline_callbacks
        def run():
            self.client = aptdaemon.client.AptClient(self.bus)
            trans = yield self.client.install_packages(["silly-depend-base"])
            trans.connect("finished", self._on_finished)
            trans.connect("medium-required", self._on_medium_required_cancel)
            yield trans.run()
            defer.return_value(trans)
        deferred = run()
        aptdaemon.loop.mainloop.run()
        self.assertEqual(deferred.result.exit, aptdaemon.enums.EXIT_CANCELLED)

        self.chroot.mount_cdrom()

        deferred = run()
        aptdaemon.loop.mainloop.run()
        self.assertEqual(deferred.result.exit, aptdaemon.enums.EXIT_SUCCESS)


if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
