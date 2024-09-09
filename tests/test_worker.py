#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Provides unit tests for the APT worker."""
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

__author__ = "Sebastian Heinlein <devel@glatzor.de>"

import glob
import netrc
import os
import shutil
import stat
import sys
import tempfile
import unittest

import apt_pkg
from gi.repository import GLib
from mock import (
    Mock,
    patch)

import aptkit.test
from aptkit.worker.aptworker import (
    AptWorker)
from aptkit.core import Transaction
from aptkit import enums, errors


REPO_PATH = os.path.join(aptkit.test.get_tests_dir(), "repo")

PY3K = sys.version_info.major > 2


class WorkerTestCase(aptkit.test.AptKitTestCase):

    """Test suite for the worker which performs the actual package
    installation and removal."""

    def setUp(self):
        self.chroot = aptkit.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        self.loop = GLib.MainLoop()
        self.queue = aptkit.test.MockQueue()
        self.worker = AptWorker(chroot=self.chroot.path, load_plugins=False)
        self.worker.connect("transaction-done", lambda w, t: self.loop.quit())
        self.worker.connect("transaction-simulated",
                            lambda w, t: self.loop.quit())

    @unittest.skipIf("nose" in sys.modules, "Fails under nosetests3")
    def test_update_cache(self):
        """Test updating the cache using a local repository."""
        # Add a working and a non-working repository
        self.chroot.add_trusted_key()
        path = os.path.join(self.chroot.path,
                            "etc/apt/sources.list.d/test.list")
        with open(path, "w") as part_file:
            part_file.write("deb file://%s ./" % REPO_PATH)
        self.chroot.add_repository("/does/not/exist", copy_list=False)
        # Only update the repository from the working snippet
        trans = Transaction(None, enums.ROLE_UPDATE_CACHE,
                            self.queue, os.getpid(), os.getuid(),
                            os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            kwargs={"sources_list": "test.list"})
        self.worker.simulate(trans)
        self.loop.run()
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        self.assertEqual(len(self.worker._cache), 10)
        pkg = self.worker._cache["silly-base"]
        self.assertTrue(pkg.candidate.origins[0].trusted)

    def test_upgrade_system(self):
        """Test upgrading the system."""
        self.chroot.add_test_repository()
        self.chroot.install_debfile(os.path.join(REPO_PATH,
                                                 "silly-base_0.1-0_all.deb"))
        # Install the package
        trans = Transaction(None, enums.ROLE_UPGRADE_SYSTEM,
                            self.queue, os.getpid(), os.getgid(),
                            os.getuid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            kwargs={"safe_mode": False})
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.depends[enums.PKGS_UPGRADE],
                         ["silly-base=0.1-0update1"])
        self.assertTrue(trans.space > 0)
        self.assertTrue(trans.download == 0)
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        # Test apt history log
        with open(os.path.join(self.chroot.path, "var/log/apt/history.log")) \
                as history_file:
            history = history_file.read()
        self.assertTrue("Commandline: aptkit role='%s'" % trans.role in
                        history)

        self.assertEqual(self.worker._cache["silly-base"].installed.version,
                         "0.1-0update1")

    def test_check_unauth(self):
        """Test if packages from an unauthenticated repo are detected."""
        self.chroot.add_test_repository(copy_sig=False)
        # Install the package
        trans = Transaction(None, enums.ROLE_INSTALL_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[["silly-base"], [], [], [], [], []])
        self.worker.simulate(trans)
        self.loop.run()
        trans.allow_unauthenticated = False
        self.assertEqual(trans.unauthenticated, ["silly-base"])
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_FAILED)
        self.assertEqual(trans.error.code, enums.ERROR_PACKAGE_UNAUTHENTICATED)

        # Allow installation of unauthenticated packages
        trans = Transaction(None, enums.ROLE_INSTALL_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[["silly-base"], [], [], [], [], []])
        trans.allow_unauthenticated = True
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.unauthenticated, ["silly-base"])
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        self.assertTrue(self.worker._cache["silly-base"].is_installed)

    def test_install(self):
        """Test installation of a package from a repository."""
        self.chroot.add_test_repository()
        # Install the package
        trans = Transaction(None, enums.ROLE_INSTALL_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[["silly-depend-base"], [], [], [],
                                      [], []])
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.depends[enums.PKGS_INSTALL],
                         ["silly-base=0.1-0update1"])
        self.assertTrue(trans.space > 0)
        self.assertTrue(trans.download == 0)
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        self.assertTrue(self.worker._cache["silly-depend-base"].is_installed)

    def test_remove_obsolete(self):
        """Test the removal of obsoleted packages."""
        for pkg in ["silly-base_0.1-0_all.deb",
                    "silly-depend-base_0.1-0_all.deb"]:
            self.chroot.install_debfile(os.path.join(REPO_PATH, pkg))
        ext_states = apt_pkg.config.find_file("Dir::State::extended_states")
        with open(ext_states, "w") as ext_states_file:
            ext_states_file.write("""Package: silly-base
Architecture: all
Auto-Installed: 1""")
        trans = Transaction(None, enums.ROLE_REMOVE_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[[], [], ["silly-depend-base"], [],
                                      [], []])
        trans.remove_obsoleted_depends = True
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.depends[enums.PKGS_REMOVE],
                         ["silly-base=0.1-0"])
        self.assertTrue(trans.space < 0)
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        self.assertFalse("silly-base" in self.worker._cache)
        self.assertFalse("silly-depend-base" in self.worker._cache)

    def test_remove(self):
        """Test the removal of packages."""
        for pkg in ["silly-base_0.1-0_all.deb",
                    "silly-essential_0.1-0_all.deb",
                    "silly-depend-base_0.1-0_all.deb"]:
            self.chroot.install_debfile(os.path.join(REPO_PATH, pkg))
        trans = Transaction(None, enums.ROLE_REMOVE_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[[], [], ["silly-base"], [], [], []])
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.depends[enums.PKGS_REMOVE],
                         ["silly-depend-base=0.1-0"])
        self.assertTrue(trans.space < 0)
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        try:
            installed = self.worker._cache["silly-depend-base"].is_installed
            self.assertFalse(installed)
        except KeyError:
            pass
        # Don't allow to remove essential packages
        trans = Transaction(None, enums.ROLE_REMOVE_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[[], [], ["silly-essential"], [], [], []])
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_FAILED,
                         "Allowed to remove an essential package")
        self.assertEqual(trans.error.code,
                         enums.ERROR_NOT_REMOVE_ESSENTIAL_PACKAGE,
                         "Allowed to remove an essential package")

    def test_upgrade(self):
        """Test upgrading of packages."""
        self.chroot.add_test_repository()
        for pkg in ["silly-base_0.1-0_all.deb",
                    "silly-depend-base_0.1-0_all.deb"]:
            self.chroot.install_debfile(os.path.join(REPO_PATH, pkg))
        ext_states = apt_pkg.config.find_file("Dir::State::extended_states")
        with open(ext_states, "w") as ext_states_file:
            ext_states_file.write("""Package: silly-base
Architecture: all
Auto-Installed: 1""")
        trans = Transaction(None, enums.ROLE_COMMIT_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[[], [], [], [],
                                      ["silly-base=0.1-0update1"], []])
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        self.assertEqual(self.worker._cache["silly-base"].installed.version,
                         "0.1-0update1", "Failed to upgrade.")
        self.assertTrue(self.worker._cache["silly-base"].is_auto_installed)

    def test_downgrade(self):
        """Test downgrading of packages."""
        self.chroot.add_test_repository()
        pkg = os.path.join(REPO_PATH, "silly-base_0.1-0update1_all.deb")
        self.chroot.install_debfile(pkg)
        trans = Transaction(None, enums.ROLE_COMMIT_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[[], [], [], [], [],
                                      ["silly-base=0.1-0"]])
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        self.assertEqual(self.worker._cache["silly-base"].installed.version,
                         "0.1-0", "Failed to downgrade.")

    def test_purge(self):
        """Test the purging of packages."""
        for pkg in ["silly-base_0.1-0_all.deb", "silly-config_0.1-0_all.deb"]:
            self.chroot.install_debfile(os.path.join(REPO_PATH, pkg))
        trans = Transaction(None, enums.ROLE_REMOVE_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            packages=[[], [], [], ["silly-config"], [], []])
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.assertFalse(
            os.path.exists(os.path.join(self.chroot.path,
                                        "etc/silly-packages.cfg")),
            "Configuration file wasn't removed.")

    def test_install_file(self):
        """Test the installation of a local package file."""
        # test
        self.chroot.add_test_repository()
        pkg = os.path.join(REPO_PATH,
                           "silly-depend-base_0.1-0_all.deb")
        trans = Transaction(None, enums.ROLE_INSTALL_FILE, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            kwargs={"path": os.path.join(REPO_PATH, pkg),
                                    "force": False})
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.depends[enums.PKGS_INSTALL],
                         ["silly-base=0.1-0update1"])
        self.assertTrue(trans.space > 0)
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        pkg = self.worker._cache["silly-depend-base"]
        self.assertTrue(pkg.is_installed)

    def test_install_conflicting_file(self):
        """Test installing of a local package file that conflicts with
        installed packages.

        Regression test for LP: #750958
        """
        pkg_base = "silly-base_0.1-0_all.deb"
        self.chroot.install_debfile(os.path.join(REPO_PATH, pkg_base))
        pkg = os.path.join(REPO_PATH, "silly-bully_0.1-0_all.deb")
        trans = Transaction(None, enums.ROLE_INSTALL_FILE, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            kwargs={"path": os.path.join(REPO_PATH, pkg),
                                    "force": True})
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_FAILED,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.assertEqual(trans.error.code, enums.ERROR_DEP_RESOLUTION_FAILED)
        self.worker._cache.open()

    def test_install_unknown_file(self):
        """Test the installation of a local package file which is not known
        to the cache.

        Regression test for LP #702217
        """
        pkg = os.path.join(REPO_PATH, "silly-base_0.1-0_all.deb")
        trans = Transaction(None, enums.ROLE_INSTALL_FILE, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False,
                            kwargs={"path": os.path.join(REPO_PATH, pkg),
                                    "force": True})
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.packages, (["silly-base"], [], [], [], [], []))
        self.assertTrue(trans.space > 0)
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        self.assertTrue(self.worker._cache["silly-base"].is_installed)

    def test_fix_broken_depends(self):
        """Test the fixing of broken dependencies."""
        for pkg in ["silly-base_0.1-0_all.deb", "silly-broken_0.1-0_all.deb"]:
            self.chroot.install_debfile(os.path.join(REPO_PATH, pkg), True)
        trans = Transaction(None, enums.ROLE_FIX_BROKEN_DEPENDS, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test", connect=False)
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.depends[enums.PKGS_REMOVE],
                         ["silly-broken=0.1-0"])
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        self.worker._cache.open()
        self.assertEqual(self.worker._cache.broken_count, 0)

    def test_install_broken_depends(self):
        """Test the that installing a package with broken dependencies
        fails in a correct way.
        """
        self.chroot.add_test_repository()
        trans = Transaction(None, enums.ROLE_COMMIT_PACKAGES, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test",
                            packages=[["silly-broken"], [], [], [], [], []],
                            connect=False)
        self.worker.simulate(trans)
        self.loop.run()
        self.assertEqual(trans.error.code, enums.ERROR_DEP_RESOLUTION_FAILED)

    def test_add_license_key_unsecure(self):
        """Test if we refuse to install license key files to an unsecure
        location or binaries."""
        self.chroot.add_test_repository(copy_sig=False)
        # Should fail because of an untrusted source
        license_key = "NASTY_BLOB"
        license_key_path = "/opt/silly-license/NASTY.KEY"
        pkg_name = "silly-license"
        self.assertRaises(errors.TransactionFailed,
                          self.worker._add_license_key_to_system,
                          pkg_name, license_key, license_key_path)
        # Check if we don't allow to install executables
        with open("/bin/ls", "rb") as sample_exec:
            license_key = sample_exec.read()
            if PY3K:
                license_key = license_key.decode("UTF-8", "ignore")
        pkg_name = "silly-license"
        self.assertRaises(errors.TransactionFailed,
                          self.worker._add_license_key_to_system,
                          pkg_name, license_key, license_key_path)

    def test_add_license_key(self):
        """Test the installation of license key files."""
        license_key = "Bli bla blub, I am a nasty BLOB!"
        license_path = "/opt/silly-license/NASTY.KEY"

        def get_license_key_mock(uid, pkg, oauth, server):
            return license_key, license_path

        self.chroot.add_test_repository()
        trans = Transaction(None, enums.ROLE_ADD_LICENSE_KEY, self.queue,
                            os.getpid(), os.getuid(), os.getgid(), sys.argv[0],
                            "org.debian.apt.test",
                            kwargs={"pkg_name": "silly-license",
                                    "json_token": "lalelu",
                                    "server_name": "mock"},
                            connect=False)
        os.makedirs(os.path.join(
            aptkit.worker.aptworker.apt_pkg.config["Dir"],
            "opt/silly-license/"))
        self.worker.plugins["get_license_key"] = [get_license_key_mock]
        self.worker.run(trans)
        self.loop.run()
        self.assertEqual(trans.exit, enums.EXIT_SUCCESS,
                         "%s: %s" % (trans._error_property[0],
                                     trans._error_property[1]))
        # Check the content of the installed key
        verify_path = os.path.join(
            aptkit.worker.aptworker.apt_pkg.config["Dir"], license_path[1:])
        with open(verify_path) as verify_file:
            self.assertEqual(license_key, verify_file.read(),
                             "Content of license key doesn't match")

    def test_use_apt_auth_conf(self):
        """Test if credentials of repositories are store securely in a
        separate file.
        """
        source_file_name = "private_source.list"
        self.worker.add_repository(Mock(), "deb",
                                   "https://user:pass@host.example.com/path",
                                   "natty", ["main"], "comment",
                                   source_file_name)
        # check if password was stripped (source file)
        source_parts = apt_pkg.config.find_dir("Dir::Etc::sourceparts")
        source_file_path = os.path.join(source_parts,
                                        source_file_name)
        with open(source_file_path) as source_file:
            source_file_content = source_file.read()
        self.assertFalse("user:pass" in source_file_content)
        # check if password was stored correctly (auth.conf)
        auth_file_path = apt_pkg.config.find_file("Dir::Etc::netrc")
        with open(auth_file_path) as auth_file:
            auth_file_content = auth_file.read()
        for token in ["login user",
                      "password pass",
                      "machine host.example.com/path"]:
            self.assertTrue(token in auth_file_content)
        buf = os.stat(auth_file_path)
        self.assertEqual(stat.S_IMODE(buf.st_mode), 0o640)
        # now add the repo again with updated auth credentials and ensure
        # that the info is not duplicated
        self.worker.add_repository(Mock(), "deb",
                                   "https://xuser:xpass@host.example.com/path",
                                   "natty", ["main"], "comment",
                                   source_file_name)
        # check if password was stored correctly (auth.conf)
        auth_file_path = apt_pkg.config.find_file("Dir::Etc::netrc")
        netrc_file = netrc.netrc(auth_file_path)
        self.assertEqual(len(netrc_file.hosts), 1)
        with open(auth_file_path) as auth_file:
            auth_file_content = auth_file.read()
        self.assertFalse("login user" in auth_file_content)
        for token in ["login xuser",
                      "password xpass",
                      "machine host.example.com/path"]:
            self.assertTrue(token in auth_file_content)
        netrc_file = netrc.netrc(auth_file_path)
        self.assertEqual(len(netrc_file.hosts), 1)
        # add another one
        self.worker.add_repository(
            Mock(), "deb", "https://user2:pass2@host.example.com/path2",
            "natty", ["main"], "comment", source_file_name)
        netrc_file = netrc.netrc(auth_file_path)
        self.assertEqual(len(netrc_file.hosts), 2)
        # change mode and add another repo
        os.chmod(auth_file_path, 0o740)
        self.worker.add_repository(Mock(), "deb",
                                   "https://user:pass@host.example.com/path3",
                                   "natty", ["main"], "comment",
                                   source_file_name)
        # and ensure auth.conf mode is kept and *not* reset
        buf = os.stat(auth_file_path)
        self.assertEqual(stat.S_IMODE(buf.st_mode), 0o740)
        self.assertEqual(len(netrc.netrc(auth_file_path).hosts), 3)

    def test_modify_apt_auth_fallback(self):
        netrc_tempfile = tempfile.NamedTemporaryFile()
        # note that the order of password/login is different than the
        # standard order
        netrc_tempfile.write("""
machine private-ppa.launchpad.net/project-foo
password baz
login foo
""".encode("utf8"))
        netrc_tempfile.flush()
        # now pretend we have a different user/pass
        uri = "http://foo2:baz2@private-ppa.launchpad.net/project-foo"
        self.worker._store_and_strip_password_from_uri(
            uri, netrc_tempfile.name)
        # ensure that it used the fallback prepend
        with open(netrc_tempfile.name) as f:
            self.assertEqual(f.read(), """
machine private-ppa.launchpad.net/project-foo login foo2 password baz2

machine private-ppa.launchpad.net/project-foo
password baz
login foo
""")
        # and another one with a new entry that just goes to the end
        # and special chars, note that the python netrc parser will fail
        # for non-ascii (yes, it does)
        uri = "http://m%20oo:bär@private-ppa.launchpad.net/project-moobar"
        self.worker._store_and_strip_password_from_uri(
            uri, netrc_tempfile.name)
        with open(netrc_tempfile.name, 'rb') as f:
            self.assertEqual(f.read().decode("utf-8"), """
machine private-ppa.launchpad.net/project-foo login foo2 password baz2

machine private-ppa.launchpad.net/project-foo
password baz
login foo

machine private-ppa.launchpad.net/project-moobar login m%20oo password bär
""")


@unittest.skipIf(not PY3K, "Only test the backend for Python3")
def setUp():
    pass


if __name__ == "__main__":
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
