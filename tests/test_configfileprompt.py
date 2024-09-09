#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the config file handling."""

import logging
import os
import time
import unittest

import defer
import dbus

import aptkit.client
import aptkit.loop
import aptkit.enums

import aptkit.test

DEBUG = True
REPO_PATH = os.path.join(aptkit.test.get_tests_dir(), "repo")


class ConfigFilePromptTestCase(aptkit.test.AptKitTestCase):

    """Test the replacement of config files."""

    def setUp(self):
        """Setup a chroot, run the aptkit and a fake PolicyKit daemon."""
        # Setup chroot
        self.chroot = aptkit.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        self.chroot.add_test_repository()
        # Start aptkit with the chroot on the session bus
        self.start_dbus_daemon()
        self.bus = dbus.bus.BusConnection(self.dbus_address)
        self.start_session_aptk(self.chroot.path)
        # Start the fake PolikcyKit daemon
        self.start_fake_polkitd()
        time.sleep(1)
        self.called = False
        # Create a fake config file which gets overwritten by silly-config
        self.config_path = os.path.join(self.chroot.path,
                                        "etc/silly-packages.cfg")
        with open(self.config_path, "w") as config:
            config.write("BliBlaBlub")

    @defer.inline_callbacks
    def _on_config_file_conflict(self, trans, config_old, config_new, answer):
        self.assertEqual(trans.config_file_conflict, (config_old, config_new))
        if answer == "urgs":
            # Check if cancelling is forbidden
            try:
                yield trans.cancel()
            except aptkit.errors.AptKitError as error:
                self.assertTrue(str(error),
                                "org.debian.aptkit: Could not cancel transaction")
            # Check if we fail correctly on wrong answers
            try:
                yield trans.resolve_config_file_conflict(config_old,
                                                         "a&&dasmk")
            except aptkit.errors.AptKitError as error:
                self.assertTrue(str(error).index("Invalid value"))
                yield trans.resolve_config_file_conflict(config_old, "replace")
            else:
                self.fail("Failed to detect invalid answer")
        else:
            yield trans.resolve_config_file_conflict(config_old, answer)

    def _on_finished(self, trans, exit):
        """Callback to stop the mainloop after a transaction is done."""
        aptkit.loop.mainloop.quit()

    def test_keep(self):
        """Test keeping the current configuration file."""
        @defer.inline_callbacks
        def run():
            self.client = aptkit.client.AptClient(self.bus)
            trans = yield self.client.install_packages(["silly-config"])
            trans.connect("finished", self._on_finished)
            trans.connect("config-file-conflict",
                          self._on_config_file_conflict,
                          "keep")
            yield trans.run()
            defer.return_value(trans)
        deferred = run()
        aptkit.loop.mainloop.run()
        self.assertEqual(deferred.result.exit, aptkit.enums.EXIT_SUCCESS)
        with open(self.config_path) as config:
            self.assertEqual(config.read(),
                             "BliBlaBlub")
        with open("%s.dpkg-dist" % self.config_path) as config_dist:
            self.assertEqual(config_dist.read(),
                             "#Just another config file.\n")

    def test_replace(self):
        """Test replacing the current configuration file."""
        @defer.inline_callbacks
        def run():
            self.client = aptkit.client.AptClient(self.bus)
            trans = yield self.client.install_packages(["silly-config"])
            trans.connect("finished", self._on_finished)
            trans.connect("config-file-conflict",
                          self._on_config_file_conflict,
                          "replace")
            yield trans.run()
            defer.return_value(trans)
        deferred = run()
        aptkit.loop.mainloop.run()
        self.assertEqual(deferred.result.exit, aptkit.enums.EXIT_SUCCESS)
        with open(self.config_path) as config:
            self.assertEqual(config.read(),
                             "#Just another config file.\n")
        with open("%s.dpkg-old" % self.config_path) as config_old:
            self.assertEqual(config_old.read(),
                             "BliBlaBlub")

    def test_fail(self):
        """Test failing correctly."""
        @defer.inline_callbacks
        def run():
            self.client = aptkit.client.AptClient(self.bus)
            trans = yield self.client.install_packages(["silly-config"])
            yield trans.set_locale("C")
            trans.connect("finished", self._on_finished)
            trans.connect("config-file-conflict",
                          self._on_config_file_conflict,
                          "urgs")
            yield trans.run()
            defer.return_value(trans)
        deferred = run()
        aptkit.loop.mainloop.run()
        self.assertEqual(deferred.result.exit, aptkit.enums.EXIT_SUCCESS)
        with open(self.config_path) as config:
            self.assertEqual(config.read(),
                             "#Just another config file.\n")
        with open("%s.dpkg-old" % self.config_path) as config_old:
            self.assertEqual(config_old.read(),
                             "BliBlaBlub")


if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
