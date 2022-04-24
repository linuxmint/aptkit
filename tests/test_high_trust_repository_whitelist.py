#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Provides unit tests for the APTDAEMON high-trust-repo feature."""
# Copyright (C) 2011 Sebastian Heinlein <devel@glatzor.de>
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

__author__ = "Michael Vogt <michael.vogt@ubuntu.com>"

import os
import sys
import time
import unittest

import dbus
from gi.repository import GLib
from mock import (
    patch)

import aptdaemon.client
from aptdaemon.policykit1 import (
    PK_ACTION_INSTALL_PACKAGES_FROM_HIGH_TRUST_REPO as PK_ACTION)
import aptdaemon.test

from aptdaemon.worker.aptworker import (
    _read_high_trust_repository_whitelist_file,
    read_high_trust_repository_dir,
    trans_only_installs_pkgs_from_high_trust_repos,
    AptWorker)
from aptdaemon.core import Transaction
from aptdaemon import enums


REPO_PATH = os.path.join(aptdaemon.test.get_tests_dir(), "repo")

PY3K = sys.version_info.major > 2


class BaseHighTrustTestCase(aptdaemon.test.AptDaemonTestCase):

    def setUp(self):
        self.chroot = aptdaemon.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        self.loop = GLib.MainLoop()


class HighTrustRepositoryTestCase(BaseHighTrustTestCase):

    """ Test the worker low-level bits of the high-trust repo implementation"""

    def setUp(self):
        super(HighTrustRepositoryTestCase, self).setUp()
        self.queue = aptdaemon.test.MockQueue()
        self.worker = AptWorker(chroot=self.chroot.path, load_plugins=False)
        self.worker.connect("transaction-done", lambda w, t: self.loop.quit())
        self.worker.connect("transaction-simulated",
                            lambda w, t: self.loop.quit())

    def test_read_high_trust_repository_whitelist_dir(self):
        whitelist = read_high_trust_repository_dir(
            os.path.join(aptdaemon.test.get_tests_dir(),
                         "data/high-trust-repository-whitelist.d"))
        self.assertEqual(
            whitelist, set([("Ubuntu", "main", "foo.*"),
                            ("Debian-Security", "non-free", "^bar$")]))

    def test_read_high_trust_repository_whitelist(self):
        whitelist = _read_high_trust_repository_whitelist_file(
            os.path.join(aptdaemon.test.get_tests_dir(),
                         "data/high-trust-repository-whitelist.cfg"))
        self.assertEqual(
            whitelist, set([("Ubuntu", "main", "foo.*"),
                            ("Debian-Security", "non-free", "^bar$")]))

    @patch("aptdaemon.worker.log")
    def test_read_high_trust_repository_whitelist_broken(self, mock_log):
        """ test that a broken repo file results in a empty whitelist """
        whitelist = _read_high_trust_repository_whitelist_file(
            os.path.join(aptdaemon.test.get_tests_dir(),
                         "data/high-trust-repository-whitelist-broken.cfg"))
        self.assertEqual(whitelist, set())
        # ensure we log a error if the config file is broken
        # Skip due to LP: #1487087
        #mock_log.error.assert_called()

    @patch("aptdaemon.worker.log")
    def test_read_high_trust_repository_whitelist_not_there(self, mock_log):
        whitelist = _read_high_trust_repository_whitelist_file(
            "lalalala-not-there-really.cfg")
        self.assertEqual(whitelist, set())
        # ensure we log no error if there is no config file
        self.assertFalse(mock_log.called)

    def test_high_trust_repository(self):
        """Test if using a high_trust repo is working """
        self.chroot.add_repository(os.path.join(aptdaemon.test.get_tests_dir(),
                                                "repo/whitelisted"))
        # setup a whitelist
        self.worker._high_trust_repositories.add(
            ("Ubuntu", "", "silly.*"))
        # a high-trust whitelisted pkg and a non-whitelisted one
        trans = Transaction(None, enums.ROLE_INSTALL_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[["silly-base", "other-pkg"], [], [], [],
                                      [], []])
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.high_trust_packages, ["silly-base"])
        self.assertFalse(
            trans_only_installs_pkgs_from_high_trust_repos(
                trans, self.worker._high_trust_repositories))
        # whitelisted only
        trans = Transaction(None, enums.ROLE_INSTALL_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[["silly-base"], [], [], [], [], []])
        self.worker.simulate(trans)
        self.loop.run()
        self.assertTrue(
            trans_only_installs_pkgs_from_high_trust_repos(
                trans, self.worker._high_trust_repositories))


class HighTrustRepositoryIntegrationTestCase(BaseHighTrustTestCase):
    """ Test the whitelist feature inside the chroot """

    def setUp(self):
        super(HighTrustRepositoryIntegrationTestCase, self).setUp()
        # Start aptdaemon with the chroot on the session bus
        self.start_dbus_daemon()
        self.bus = dbus.bus.BusConnection(self.dbus_address)
        # setup the environment first including the high-trust whitelist
        self.chroot.add_repository(os.path.join(aptdaemon.test.get_tests_dir(),
                                                "repo/whitelisted"))
        whitelist_file = os.path.join(
            self.chroot.path, "etc", "aptdaemon",
            "high-trust-repository-whitelist.d", "test.cfg")
        os.makedirs(os.path.dirname(whitelist_file))

        with open(whitelist_file, "w") as f:
            f.write("""
[test repo"]
origin = Ubuntu
component =
pkgnames = silly.*
""")
        # *after* that start the aptdaemon
        self.start_session_aptd(self.chroot.path)
        time.sleep(1)
        # start policykit and *only* allow from-whitelisted repo pk action
        self.start_fake_polkitd(PK_ACTION)
        time.sleep(1)

    def test_high_trust_polkit_ok(self):
        self.client = aptdaemon.client.AptClient(self.bus)
        # test that the high trust whitelist works
        trans = self.client.install_packages(["silly-base"])
        trans.simulate()
        trans.connect("finished", lambda a, b: self.loop.quit())
        trans.run()
        self.loop.run()
        self.assertEqual(trans.exit, aptdaemon.enums.EXIT_SUCCESS)
        # plus ensure removal will not work
        trans = self.client.remove_packages(["silly-base"])
        with self.assertRaises(aptdaemon.errors.NotAuthorizedError):
            trans.run()

    def test_high_trust_polkit_not_ok(self):
        self.client = aptdaemon.client.AptClient(self.bus)
        # ensure that non-whitelisted packages can not be installed
        trans = self.client.install_packages(["other-pkg"])
        trans.simulate()
        trans.connect("finished", lambda a, b: self.loop.quit())
        with self.assertRaises(aptdaemon.errors.NotAuthorizedError):
            trans.run()


if __name__ == "__main__":
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
