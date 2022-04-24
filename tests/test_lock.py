#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests locking."""

import logging
import os
import socket
import subprocess
import sys
import unittest

import aptdaemon.test

import aptdaemon.worker.aptworker

DEBUG = False

import apt_pkg
apt_pkg.init()


class LockTest(unittest.TestCase):

    REMOTE_REPO = "deb copy://%s/repo ./" % aptdaemon.test.get_tests_dir()

    def setUp(self):
        self.chroot = aptdaemon.test.Chroot("-lock-test")
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        # Required to change the lock pathes to the chroot
        self.worker = aptdaemon.worker.aptworker.AptWorker(
            chroot=self.chroot.path,
            load_plugins=False)
        pkg_path = os.path.join(aptdaemon.test.get_tests_dir(),
                                "repo/silly-base_0.1-0_all.deb")
        self.dpkg_cmd = ["fakeroot", "dpkg", "--root", self.chroot.path,
                         "--log=%s/var/log/dpkg.log" % self.chroot.path,
                         "--install", pkg_path]
        self.inst_cmd = ('apt-get install silly-base '
                         '-o "Dir"="%s" '
                         '-o "Dir::state::status"="%s/var/lib/dpkg/status" '
                         '-o "Dir::Bin::Dpkg"="%s/dpkg-wrapper.sh" '
                         '-o "DPkg::Options::"="--root=%s" -y --force-yes' %
                         (self.chroot.path, self.chroot.path,
                          aptdaemon.test.get_tests_dir(), self.chroot.path))
        self.apt_cmd = ('apt-get update -o "Dir"="%s" -o "Dir::state::status="'
                        '"%s/var/lib/dpkg/status"' %
                        (self.chroot.path, self.chroot.path))
        # ensure to kill /etc/apt/apt.conf.d, otherwise stuff like
        # the (root only) Dpkg::Post-Invoke actions are run
        with open("%s/etc/apt/apt.conf" % self.chroot.path, "w") as conf:
            conf.write('Dir::Etc::parts "/directory-does-not-exist";')
        self.env = {
            # override the default apt conf to kill off apt.conf.d includes
            "APT_CONFIG": "%s/etc/apt/apt.conf" % self.chroot.path,
            # provide a path for dpkg
            "PATH": "/sbin:/bin:/usr/bin:/usr/sbin"}

    def test_global_lock(self):
        """Check if the lock blocks dpkg and apt-get."""
        # Lock!
        aptdaemon.worker.aptworker.lock.acquire()
        self.assertEqual(2, subprocess.call(self.dpkg_cmd, env=self.env))
        self.assertEqual(100, subprocess.call(self.apt_cmd, env=self.env,
                         shell=True))
        # Relase and all should work again!
        aptdaemon.worker.aptworker.lock.release()
        self.assertEqual(0, subprocess.call(self.dpkg_cmd, env=self.env))
        self.assertEqual(0, subprocess.call(self.apt_cmd, env=self.env,
                         shell=True))

    def test_status_lock(self):
        """Test the lock on the status lock."""
        # Lock!
        aptdaemon.worker.aptworker.lock.status_lock.acquire()
        self.assertEqual(2, subprocess.call(self.dpkg_cmd, env=self.env))
        self.assertEqual(0, subprocess.call(self.apt_cmd, env=self.env,
                         shell=True))
        # Relase and all should work again!
        aptdaemon.worker.aptworker.lock.status_lock.release()
        self.assertEqual(0, subprocess.call(self.dpkg_cmd, env=self.env))
        self.assertEqual(0, subprocess.call(self.apt_cmd, env=self.env,
                         shell=True))

    def test_lists_lock(self):
        """Test the lock on the repository packages lists."""
        # Lock!
        aptdaemon.worker.aptworker.lock.lists_lock.acquire()
        # Dpkg doesn't care about the lock
        self.assertEqual(0, subprocess.call(self.dpkg_cmd, env=self.env))
        self.assertEqual(100, subprocess.call(self.apt_cmd, env=self.env,
                         shell=True))
        # Relase and all should work again!
        aptdaemon.worker.aptworker.lock.lists_lock.release()
        self.assertEqual(0, subprocess.call(self.apt_cmd, env=self.env,
                         shell=True))

    def test_archives_lock(self):
        """Test the lock on the download archives."""
        # Skip the test if we don't have networking
        aptdaemon.worker.aptworker.lock.archive_lock.acquire()
        lst_path = os.path.join(self.chroot.path, "etc/apt/sources.list")
        with open(lst_path, "w") as lst_file:
            lst_file.write(self.REMOTE_REPO)
        # Dpkg and apt-get doen't care about the lock as long as there aren't
        # any downloads required
        self.assertEqual(0, subprocess.call(self.dpkg_cmd, env=self.env))
        self.assertEqual(100, subprocess.call(self.apt_cmd, env=self.env,
                         shell=True))
        self.assertEqual(100, subprocess.call(self.inst_cmd, env=self.env,
                         shell=True))
        # Relase and all should work again!
        aptdaemon.worker.aptworker.lock.archive_lock.release()
        self.assertEqual(0, subprocess.call(self.inst_cmd, env=self.env,
                         shell=True))


@unittest.skipIf(sys.version_info.major < 3, "Python 3 only")
def setUp():
    pass

if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
