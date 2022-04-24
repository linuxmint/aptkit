#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the client module."""

import logging
import time
import unittest

import dbus
import defer

from gi.repository import GObject

import aptdaemon.client
import aptdaemon.loop
import aptdaemon.enums
import aptdaemon.errors

import aptdaemon.test

DEBUG = True


class ClientTestNotAuthorized(aptdaemon.test.AptDaemonTestCase):

    """Test the python client."""

    def setUp(self):
        """Setup a chroot, run the aptdaemon and a fake PolicyKit daemon."""
        # Setup chroot
        self.chroot = aptdaemon.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        self.chroot.add_test_repository()
        # Start aptdaemon with the chroot on the session bus
        self.start_dbus_daemon()
        self.bus = dbus.bus.BusConnection(self.dbus_address)
        self.start_session_aptd(self.chroot.path)
        # Start the fake PolikcyKit daemon and disallow all actions
        self.start_fake_polkitd("none")
        time.sleep(1)

    def _on_finished(self, trans, exit):
        """Callback to stop the mainloop after a transaction is done."""
        aptdaemon.loop.mainloop.quit()

    def test_auth_failed(self):
        """Test the failing of an unauthorized transaction"""
        @defer.inline_callbacks
        def run():
            self.client = aptdaemon.client.AptClient(self.bus)
            trans = yield self.client.update_cache()
            trans.connect("finished", self._on_finished)
            try:
                yield trans.run()
            except aptdaemon.errors.NotAuthorizedError as error:
                print(error)
            except Exception as error:
                self.fail("Wrong exception: %s" % error)
            else:
                self.fail("Authorization passed (sic!)")
            defer.return_value(trans)
        deferred = run()
        aptdaemon.loop.mainloop.run()
        self.assertEqual(deferred.result.error.code,
                         aptdaemon.enums.ERROR_NOT_AUTHORIZED)


class ClientTest(aptdaemon.test.AptDaemonTestCase):

    """Test the python client."""

    def setUp(self):
        """Setup a chroot, run the aptdaemon and a fake PolicyKit daemon."""
        # Setup chroot
        self.chroot = aptdaemon.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        self.chroot.add_test_repository()
        self.chroot.add_trusted_key()
        # Start aptdaemon with the chroot on the session bus
        self.start_dbus_daemon()
        self.bus = dbus.bus.BusConnection(self.dbus_address)
        self.start_session_aptd(self.chroot.path)
        # Start the fake PolikcyKit daemon
        self.start_fake_polkitd()
        time.sleep(1)

    def _on_finished(self, trans, exit):
        """Callback to stop the mainloop after a transaction is done."""
        aptdaemon.loop.mainloop.quit()

    def test_sync(self):
        """Test synchronous calls to the client."""
        self.client = aptdaemon.client.AptClient(self.bus)
        trans = self.client.update_cache()
        trans.connect("finished", self._on_finished)
        trans.run()
        aptdaemon.loop.mainloop.run()
        self.assertEqual(trans.exit, aptdaemon.enums.EXIT_SUCCESS)

    def test_deferred(self):
        """Test deferred calls to the client."""
        @defer.inline_callbacks
        def run():
            self.client = aptdaemon.client.AptClient(self.bus)
            trans = yield self.client.update_cache()
            trans.connect("finished", self._on_finished)
            yield trans.run()
            defer.return_value(trans)
        deferred = run()
        aptdaemon.loop.mainloop.run()
        self.assertEqual(deferred.result.exit, aptdaemon.enums.EXIT_SUCCESS)

    def test_client_methods_sync(self):
        """ Test most client methods (syncronous) """
        test_methods = [
            ("enable_distro_component", ("universe",)),
            ("add_repository", ("deb", "http://archive.ubuntu.com/ubuntu",
                                "lucid", "restricted"))]
        client = aptdaemon.client.AptClient(self.bus)
        for (method, args) in test_methods:
            f = getattr(client, method)
            exit = f(*args, wait=True)
            self.assertEqual(exit, aptdaemon.enums.EXIT_SUCCESS)

    def test_simulation_error(self):
        """Test if a simulation fails in a correct way."""
        @defer.inline_callbacks
        def run():
            self.client = aptdaemon.client.AptClient(self.bus)
            trans = yield self.client.install_packages(["silly-broken"])
            trans.connect("finished", self._on_finished)
            yield trans.simulate()
            self.fail("We should never have been here")
            yield trans.run()
            defer.return_value(trans)
        deferred = run()
        aptdaemon.loop.mainloop.run()
        self.assertEqual(deferred.result.value.code,
                         aptdaemon.enums.ERROR_DEP_RESOLUTION_FAILED)

    def test_run_error(self):
        """Test if a simulation during run fails in a correct way."""
        @defer.inline_callbacks
        def run():
            self.client = aptdaemon.client.AptClient(self.bus)
            trans = yield self.client.install_packages(["silly-broken"])
            trans.connect("finished", self._on_finished)
            yield trans.run()
            self.fail("We should never have been here")
            defer.return_value(trans)
        deferred = run()
        aptdaemon.loop.mainloop.run()
        self.assertEqual(deferred.result.value.code,
                         aptdaemon.enums.ERROR_DEP_RESOLUTION_FAILED)

    def test_tid_caching(self):
        """Test if calling Client with identical TIDs uses caching."""

        tid = "/meep"
        trans = aptdaemon.client.AptTransaction(tid, bus=self.bus)
        trans2 = aptdaemon.client.AptTransaction(tid, bus=self.bus)
        trans3 = aptdaemon.client.AptTransaction("/meep2", bus=self.bus)
        self.assertEqual(trans, trans2)
        self.assertNotEqual(trans, trans3)


if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
