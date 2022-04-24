#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the PackageKit compatibility layer.

Since the PackageKit client doesn't support changing system D-Bus sockets,
run the tests only by using nose (e.g. nosetests3 tests.test_pk.PackageKitTest)
or by running the main routine (python3 test_pk.py).

If a test fails all subsequent ones will fail, too. You will get the following
error message:
gi._glib.GError: GDBus.Error:org.freedesktop.DBus.Error.ServiceUnknown:
The name :1.16 was not provided by any .service files
"""

import atexit
import logging
import os
import os.path
import shutil
import subprocess
import tempfile
import time
import sys
import unittest

import apt_pkg
import apt.auth
from gi.repository import GLib
from gi.repository import PackageKitGlib as pk

import aptdaemon.test

REPO_PATH = os.path.join(aptdaemon.test.get_tests_dir(), "repo")
DEBUG = True


@unittest.skip("Removed PackageKit compat")
class PackageKitTest(aptdaemon.test.AptDaemonTestCase):

    """Test the PackageKit compatibility layer."""

    def setUp(self):
        """Setup a chroot, run the aptdaemon and a fake PolicyKit daemon."""
        # Setup chroot
        self.chroot = aptdaemon.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)
        self.chroot.add_test_repository()
        # set up scratch dir
        self.workdir = tempfile.mkdtemp()
        # allow tests to add plugins, etc.
        self.orig_pythonpath = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = "%s:%s" % (self.workdir,
                                              os.environ.get("PYTHONPATH", ""))
        # write apt config for calling apt-key
        apt_conf = os.path.join(self.chroot.path, 'aptconfig')
        with open(apt_conf, 'w') as f:
            f.write('Dir "%s";\n' % self.chroot.path)
        os.environ['APT_CONFIG'] = apt_conf

        # if tests install keys, have aptd query a local fake server
        os.environ['APTDAEMON_KEYSERVER'] = 'hkp://localhost:19191'

        self.start_session_aptd(self.chroot.path)
        # Start the fake PolikcyKit daemon
        self.start_fake_polkitd()
        time.sleep(2.0)

    def tearDown(self):
        shutil.rmtree(self.workdir)
        if self.orig_pythonpath:
            os.environ["PYTHONPATH"] = self.orig_pythonpath

    def test_install(self):
        """Test installing a package."""
        pkg_name = "silly-depend-base"

        client = pk.Client()

        # Resolve the id of the package
        res = client.resolve(pk.FilterEnum.NONE, [pkg_name], None,
                             lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        ids = []
        for pkg in res.get_package_array():
            self.assertEqual(pkg.get_name(), pkg_name)
            ids.append(pkg.get_id())
            break
        else:
            self.fail("Failed to resolve %s" % pkg_name)

        # Simulate
        res = client.install_packages(2 ** pk.TransactionFlagEnum.SIMULATE,
                                      ids, None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        for pkg in res.get_package_array():
            self.assertEqual(pkg.get_name(), "silly-base")
            self.assertEqual(pkg.get_info(),
                             pk.info_enum_from_string("installing"))
            break
        else:
            self.fail("Failed to get dependencies of %s" % pkg_name)

        # Install
        res = client.install_packages(pk.TransactionFlagEnum.NONE, ids, None,
                                      lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)

        # verify list of files
        res = client.get_files(ids, None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        files = res.get_files_array()[0].get_property('files')
        # ships two files, plus directories
        self.assertGreaterEqual(len(files), 2,
                                'expect two files in ' + str(files))
        self.assertTrue('/usr/share/doc/silly-depend-base/copyright' in files,
                        files)

    def test_install_files(self):
        """Test installing local package files."""

        path_pkg_config = os.path.join(
            REPO_PATH,
            "silly-config_.1-0_all.deb")
        path_pkg = os.path.join(
            REPO_PATH,
            "silly-depend-base_0.1-0_all.deb")

        client = pk.Client()

        # Fail if more than package should be installed
        try:
            client.install_files(pk.TransactionFlagEnum.NONE,
                                 [path_pkg_config, path_pkg], None,
                                 lambda p, t, d: True, None)
        except GLib.GError as error:
            self.assertTrue("Only one package" in error.message)
        else:
            self.fail("Installing multiple package files didn't fail")

        # Check simulating
        res = client.install_files(2 ** pk.TransactionFlagEnum.SIMULATE,
                                   [path_pkg], None,
                                   lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = res.get_package_array()
        if len(pkgs) != 1:
            self.fail("Failed to get dependencies")
        self.assertEqual(pkgs[0].get_name(), "silly-base")
        self.assertEqual(pkgs[0].get_version(), "0.1-0update1")

        # Check the actual installtion
        res = client.install_files(pk.TransactionFlagEnum.NONE,
                                   [path_pkg], None,
                                   lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)

        # verify list of files
        res = client.get_files(["silly-depend-base;0.1-0;all;"],
                               None, lambda p, t, d: True, None)
        files = res.get_files_array()[0].get_property('files')
        # ships two files, plus directories
        self.assertGreaterEqual(len(files), 2,
                                'expect two files in ' + str(files))
        self.assertTrue('/usr/share/doc/silly-depend-base/copyright' in files,
                        files)

    def test_download(self):
        """Test downloading packages."""
        pkg_filename = "silly-base_0.1-0update1_all.deb"
        pkg_id = "silly-base;0.1-0update1;all;"
        temp_dir = tempfile.mkdtemp(prefix="aptd-download-test-")

        client = pk.Client()
        res = client.download_packages([pkg_id], temp_dir,
                                       None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        if not os.path.exists(os.path.join(temp_dir, pkg_filename)):
            self.fail("Failed to download the package")

        shutil.rmtree(temp_dir)

    def test_filters(self):
        """Test filters."""
        pkg = "silly-base_0.1-0_all.deb"
        self.chroot.install_debfile(os.path.join(REPO_PATH, pkg), True)

        client = pk.Client()

        # All version
        res = client.resolve(pk.FilterEnum.NONE, ["silly-base"], None,
                             lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = res.get_package_array()
        if len(pkgs) != 2:
            self.fail("Failed to get versions")
        versions = ["0.1-0", "0.1-0update1"]
        for pkg in pkgs:
            self.assertEqual(pkg.get_name(), "silly-base")
            versions.remove(pkg.get_version())

        # Newest version
        res = client.resolve(2 ** pk.FilterEnum.NEWEST, ["silly-base"], None,
                             lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = res.get_package_array()
        if len(pkgs) != 1:
            self.fail("Failed to get version")
        self.assertEqual(pkgs[0].get_name(), "silly-base")
        self.assertEqual(pkgs[0].get_version(), "0.1-0update1")

        # Installed version
        res = client.resolve(2 ** pk.FilterEnum.INSTALLED, ["silly-base"],
                             None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = res.get_package_array()
        if len(pkgs) != 1:
            self.fail("Failed to get version")
        self.assertEqual(pkgs[0].get_name(), "silly-base")
        self.assertEqual(pkgs[0].get_version(), "0.1-0")

        # Available version
        res = client.resolve(2 ** pk.FilterEnum.NOT_INSTALLED, ["silly-base"],
                             None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = res.get_package_array()
        if len(pkgs) != 1:
            self.fail("Failed to get version")
        self.assertEqual(pkgs[0].get_name(), "silly-base")
        self.assertEqual(pkgs[0].get_version(), "0.1-0update1")

    def test_get_updates(self):
        """Test getting updates."""
        pkg = "silly-base_0.1-0_all.deb"
        self.chroot.install_debfile(os.path.join(REPO_PATH, pkg), True)

        client = pk.Client()

        res = client.get_updates(pk.FilterEnum.NONE, None,
                                 lambda p, t, d: True, None)
        for pkg in res.get_package_array():
            self.assertEqual(pkg.get_name(), "silly-base")
            self.assertEqual(pkg.get_version(), "0.1-0update1")
            self.assertEqual(pkg.get_info(),
                             pk.info_enum_from_string("normal"))
            break
        else:
            self.fail("Failed to detect upgrade")
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)

    def test_get_updates_security(self):
        """Test if security updates are detected correctly."""
        self.chroot.add_repository(os.path.join(aptdaemon.test.get_tests_dir(),
                                                "repo/security"))
        pkg = "silly-base_0.1-0_all.deb"
        self.chroot.install_debfile(os.path.join(REPO_PATH, pkg), True)

        client = pk.Client()

        res = client.get_updates(pk.FilterEnum.NONE, None,
                                 lambda p, t, d: True, None)
        for pkg in res.get_package_array():
            self.assertEqual(pkg.get_name(), "silly-base")
            self.assertEqual(pkg.get_version(), "0.1-0update1")
            self.assertEqual(pkg.get_info(),
                             pk.info_enum_from_string("security"))
            break
        else:
            self.fail("Failed to detect upgrade")
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)

    def test_get_updates_backports(self):
        """Test if backports are detected correctly."""
        self.chroot.add_repository(os.path.join(aptdaemon.test.get_tests_dir(),
                                                "repo/backports"))
        pkg = "silly-base_0.1-0_all.deb"
        self.chroot.install_debfile(os.path.join(REPO_PATH, pkg), True)

        client = pk.Client()

        res = client.get_updates(pk.FilterEnum.NONE, None,
                                 lambda p, t, d: True, None)
        for pkg in res.get_package_array():
            self.assertEqual(pkg.get_name(), "silly-base")
            self.assertEqual(pkg.get_version(), "0.1-0update1")
            self.assertEqual(pkg.get_info(),
                             pk.info_enum_from_string("enhancement"))
            break
        else:
            self.fail("Failed to detect upgrade")
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)

    def test_require_restart(self):
        """Test if the restart-required signal gets emitted."""
        os.makedirs(os.path.join(self.chroot.path, "var/run"))
        with open(os.path.join(self.chroot.path, "var/run/reboot-required"),
                  "w") as reboot_stamp:
            reboot_stamp.write("")
        client = pk.Client()

        res = client.get_updates(pk.FilterEnum.NONE, None,
                                 lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        self.assertEqual(res.get_require_restart_worst(),
                         pk.RestartEnum.SYSTEM)

    def test_dependencies(self):
        """Test getting dependencies and dependants."""
        pkg_id_depend = "silly-depend-base;0.1-0;all;"
        pkg_id = "silly-base;0.1-0update1;all;"

        client = pk.Client()

        # Get depends
        res = client.get_depends(pk.FilterEnum.NONE, [pkg_id_depend], True,
                                 None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        for pkg in res.get_package_array():
            self.assertEqual(pkg.get_id(), pkg_id)
            break
        else:
            self.fail("Failed to get dependencies of %s" % pkg_id_depend)

        # Get requires
        res = client.get_requires(pk.FilterEnum.NONE, [pkg_id], True,
                                  None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        for pkg in res.get_package_array():
            self.assertEqual(pkg.get_id(), pkg_id_depend)
            break
        else:
            self.fail("Failed to get dependants of %s" % pkg_id)

    def test_what_provides_unsupported(self):
        """Test querying for provides for unsupported type."""

        client = pk.Client()

        try:
            client.what_provides(pk.FilterEnum.NONE, pk.ProvidesEnum.CODEC,
                                 ["gstreamer0.10(decoder-audio/ac3)"],
                                 None, lambda p, t, d: True, None)
            self.fail("expected GLib.Error failure")
        except GLib.GError as e:
            self.assertTrue("codec" in str(e), e)
            self.assertTrue("not supported" in str(e), e)

    def test_what_provides_plugin(self):
        """Test querying for provides with plugins."""

        # add plugin for extra codecs
        f = open(os.path.join(self.workdir, "extra_codecs.py"), "w")
        f.write("""import aptdaemon.pkenums as enums

def fake_what_provides(cache, type, search):
    if type in (enums.PROVIDES_CODEC, enums.PROVIDES_ANY):
        if search.startswith('gstreamer'):
            return [cache["gstreamer0.10-silly"]]
    raise NotImplementedError('cannot handle type ' + str(type))
""")
        f.close()
        os.mkdir(os.path.join(self.workdir, "extra_codecs-0.egg-info"))
        f = open(os.path.join(self.workdir, "extra_codecs-0.egg-info",
                 'entry_points.txt'), "w")
        f.write("[packagekit.apt.plugins]\n"
                "what_provides=extra_codecs:fake_what_provides\n")
        f.close()

        # invalid plugin, should not stop the valid ones
        os.mkdir(os.path.join(self.workdir, "nonexisting-1.egg-info"))
        f = open(os.path.join(self.workdir, "nonexisting-1.egg-info",
                              'entry_points.txt'), "w")
        f.write("[packagekit.apt.plugins]\n"
                "what_provides=nonexisting:what_provides\n")
        f.close()

        # another plugin to test chaining and a new type
        f = open(os.path.join(self.workdir, "more_stuff.py"), "w")
        f.write("""import aptdaemon.pkenums as enums

def my_what_provides(cache, type, search):
    if type in (enums.PROVIDES_CODEC, enums.PROVIDES_ANY):
        if search.startswith('gstreamer'):
            return [cache["silly-base"]]
    if type in (enums.PROVIDES_LANGUAGE_SUPPORT, enums.PROVIDES_ANY):
        if search.startswith('locale('):
            return [cache["silly-important"]]
    raise NotImplementedError('cannot handle type ' + str(type))
""")
        f.close()
        os.mkdir(os.path.join(self.workdir, "more_stuff-0.egg-info"))
        f = open(os.path.join(self.workdir, "more_stuff-0.egg-info",
                              'entry_points.txt'), "w")
        f.write("[packagekit.apt.plugins]\n"
                "what_provides=more_stuff:my_what_provides\n")
        f.close()

        client = pk.Client()

        # search for CODEC
        res = client.what_provides(pk.FilterEnum.NONE, pk.ProvidesEnum.CODEC,
                                   ["gstreamer0.10(decoder-audio/vorbis)"],
                                   None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = [p.get_id().split(";")[0] for p in res.get_package_array()]
        self.assertEqual(pkgs, ["gstreamer0.10-silly", "silly-base"])

        # search for LANGUAGE_SUPPORT
        res = client.what_provides(pk.FilterEnum.NONE,
                                   pk.ProvidesEnum.LANGUAGE_SUPPORT,
                                   ["locale(de_DE)"],
                                   None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = [p.get_id().split(";")[0] for p in res.get_package_array()]
        self.assertEqual(pkgs, ["silly-important"])

        # search ANY
        res = client.what_provides(pk.FilterEnum.NONE, pk.ProvidesEnum.ANY,
                                   ["gstreamer0.10(decoder-audio/vorbis)"],
                                   None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = [p.get_id().split(";")[0] for p in res.get_package_array()]
        self.assertEqual(pkgs, ["gstreamer0.10-silly", "silly-base"])

        res = client.what_provides(pk.FilterEnum.NONE, pk.ProvidesEnum.ANY,
                                   ["locale(de_DE)"],
                                   None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        pkgs = [p.get_id().split(";")[0] for p in res.get_package_array()]
        self.assertEqual(pkgs, ["silly-important"])

        res = client.what_provides(pk.FilterEnum.NONE, pk.ProvidesEnum.ANY,
                                   ["modalias(pci:1)"],
                                   None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        self.assertEqual(res.get_package_array(), [])

        # unsupported type with plugins
        try:
            client.what_provides(pk.FilterEnum.NONE,
                                 pk.ProvidesEnum.PLASMA_SERVICE,
                                 ["plasma4(dataengine-weather)"],
                                 None, lambda p, t, d: True, None)
            self.fail("expected GLib.Error failure")
        except GLib.GError as e:
            self.assertTrue("plasma" in str(e), e)
            self.assertTrue("not supported" in str(e), e)

    def test_repo_enable(self):
        """Test adding a repository."""
        client = pk.Client()

        # create test update repo
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo)
        with open(os.path.join(repo, 'Packages'), 'w') as f:
            f.write('''Package: silly-new
Priority: extra
Section: admin
Installed-Size: 44
Maintainer: Sebastian Heinlein <devel@glatzor.de>
Architecture: all
Source: silly-new (0.1-0)
Version: 1.2.3
Filename: %s/silly-base_0.1-0update1_all.deb
Size: 1934
MD5sum: 8e20af56a63a1e0cf40db3b0d07e7989
SHA1: 7ce87423d9c7a734478c464021994944d07fbf1b
SHA256: d3693c0e3e7a9519b2833fdf1301c7e03e0620edf15b95b4c7329d9eb0bee553
Description: new package from a third-party repo
''' % self.chroot.path)

        # without the new repo, we do not have it yet
        self.assertRaises(GLib.GError, client.resolve, pk.FilterEnum.NONE,
                          ['silly-new'], None, lambda p, t, d: True, None)

        # now add the new repo
        apt_source = 'deb file://%s /' % repo
        res = client.repo_enable(apt_source, True, None,
                                 lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)

        with open(os.path.join(self.chroot.path, 'etc', 'apt',
                  'sources.list')) as f:
            for line in f:
                if line.strip() == apt_source:
                    break
            else:
                self.fail('did not find newly added repository in '
                          'sources.list')

        # should not actually download the indexes yet
        self.assertRaises(GLib.GError, client.resolve, pk.FilterEnum.NONE,
                          ['silly-new'], None, lambda p, t, d: True, None)

        res = client.refresh_cache(False, None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)

        # we should now see the new package
        res = client.resolve(pk.FilterEnum.NONE, ['silly-new'], None,
                             lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)
        packages = res.get_package_array()
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0].get_name(), "silly-new")
        self.assertEqual(packages[0].get_version(), "1.2.3")
        self.assertEqual(packages[0].get_info(),
                         pk.info_enum_from_string("available"))

    def test_repo_enable_errors(self):
        """Test errors when adding a repository."""
        client = pk.Client()
        client.set_locale("C")

        try:
            client.repo_enable('bogus', True, None, lambda p, t, d: True, None)
        except GLib.GError as e:
            self.assertTrue('format' in str(e))
            self.assertTrue('bogus' in str(e))

        try:
            client.repo_enable('deb http://example.com', True, None,
                               lambda p, t, d: True, None)
        except GLib.GError as e:
            self.assertTrue('format' in str(e), e)
            self.assertTrue('http://example.com' in str(e), e)

    def test_install_signature(self):
        """Test installing a new GPG key"""
        # we do not have any key initially
        self.assertEqual(len(apt.auth.list_keys()), 0)

        # launch our keyserver
        self.start_keyserver()

        # now add one
        client = pk.Client()
        res = client.install_signature(
            pk.SigTypeEnum.GPG,
            'D0BF65B7DBE28DB62BEDBF1B683C53C7CF982D18',
            '', None, lambda p, t, d: True, None)
        self.assertEqual(res.get_exit_code(), pk.ExitEnum.SUCCESS)

        # key was imported correctly
        key = apt.auth.list_keys()[0]
        self.assertEqual('CF982D18', key.keyid)

    def test_install_signature_error(self):
        """Test installing a new GPG key with failing server"""

        # do not start keyserver, so http://localhost.. will not exist
        client = pk.Client()
        client.set_locale("C")
        try:
            client.install_signature(
                pk.SigTypeEnum.GPG,
                '1111111111111111111111111111111111111111',
                '', None, lambda p, t, d: True, None)
        except GLib.GError as e:
            self.assertTrue('Failed to download' in str(e), e)
            self.assertTrue('11111111' in str(e), e)

    def test_unimplemented(self):
        """Test proper error message on unimplemented method."""
        client = pk.Client()
        client.set_locale("C")
        try:
            client.upgrade_system("sid", pk.UpgradeKindEnum.COMPLETE, None,
                                  lambda p, t, d: True, None)
        except GLib.GError as e:
            self.assertTrue('implemented' in str(e))


@unittest.skipIf(sys.version_info.major < 3, "Python3 only")
def setUp():
    """The PackageKit client cannot handle a changed system D-Bus address.
    So we need to setup a static one for the whole test suite.

    This requires to run nosetests to launch this test suite.
    """
    proc, address = aptdaemon.test.start_dbus_daemon()
    os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = address
    # The pk.Client uses a DBus connection with exit-on-disconnect set to
    # True which cannot be modified. Furthermore the registered signal
    # handlers cannot be removed. Since GIO would kill the test suite if
    # the daemon disappears we have to delay killing the daemon
    atexit.register(os.kill, proc.pid, 9)


def tearDown():
    os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = ""


if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    setUp()
    unittest.main()
    tearDown()

# vim: ts=4 et sts=4
