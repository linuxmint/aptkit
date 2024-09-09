#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Small helpers for the test suite."""
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
__all__ = ("get_tests_dir", "Chroot", "AptKitTestCase")

import inspect
import os
import shutil
import subprocess
import sys
import time
import tempfile
import unittest

if sys.version_info.major > 2:
    from http.server import HTTPServer
    from http.server import SimpleHTTPRequestHandler as HTTPRequestHandler
else:
    from BaseHTTPServer import HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler as HTTPRequestHandler

import apt_pkg
import apt.auth

PY3K = sys.version_info.major > 2


class MockQueue(object):

    """A fake TransactionQueue which only provides a limbo attribute."""

    def __init__(self):
        self.limbo = {}


class Chroot(object):

    """Provides a chroot which can be used by APT."""

    def __init__(self, prefix="tmp"):
        self.path = tempfile.mkdtemp(prefix)

    def setup(self):
        """Setup the chroot and modify the apt configuration."""
        for subdir in ["alternatives", "info", "parts", "updates", "triggers"]:
            path = os.path.join(self.path, "var", "lib", "dpkg", subdir)
            os.makedirs(path)
        for fname in ["status", "available"]:
            with open(os.path.join(self.path, "var", "lib", "dpkg", fname),
                      "w"):
                pass
        os.makedirs(os.path.join(self.path, "var/cache/apt/archives/partial"))
        os.makedirs(os.path.join(self.path, "var/lib/apt/lists"))
        os.makedirs(os.path.join(self.path, "var/lib/apt/lists/partial"))
        os.makedirs(os.path.join(self.path, "etc/apt/apt.conf.d"))
        os.makedirs(os.path.join(self.path, "etc/apt/sources.list.d"))
        os.makedirs(os.path.join(self.path, "etc/apt/preferences.d"))
        os.makedirs(os.path.join(self.path, "etc/apt/trusted.gpg.d"))
        os.makedirs(os.path.join(self.path, "var/log"))
        os.makedirs(os.path.join(self.path, "media"))

        # Make apt use the new chroot
        dpkg_wrapper = os.path.join(get_tests_dir(), "dpkg-wrapper.sh")
        apt_key_wrapper = os.path.join(get_tests_dir(), "fakeroot-apt-key")
        config_path = os.path.join(self.path, "etc/apt/apt.conf.d/10chroot")
        with open(config_path, "w") as cnf:
            cnf.write("Dir::Bin::DPkg %s;" % dpkg_wrapper)
            cnf.write("Dir::Bin::Apt-Key %s;" % apt_key_wrapper)
        apt_pkg.read_config_file(apt_pkg.config, config_path)
        apt_pkg.init_system()
        apt_pkg.config["Dir"] = self.path

    def remove(self):
        """Remove the files of the chroot."""
        apt_pkg.config.clear("Dir")
        apt_pkg.config.clear("Dir::State::Status")
        apt_pkg.init()
        shutil.rmtree(self.path)

    def add_trusted_key(self):
        """Add glatzor's key to the trusted ones."""
        apt.auth.add_key_from_file(os.path.join(get_tests_dir(),
                                                "repo/glatzor.gpg"))

    def install_debfile(self, path, force_depends=False):
        """Install a package file into the chroot."""
        cmd_list = ["fakeroot", "dpkg", "--root", self.path,
                    "--log=%s/var/log/dpkg.log" % self.path]
        if force_depends:
            cmd_list.append("--force-depends")
        cmd_list.extend(["--install", path])
        cmd = subprocess.Popen(cmd_list,
                               env={"PATH": "/sbin:/bin:/usr/bin:/usr/sbin"})
        cmd.communicate()

    def add_test_repository(self, copy_list=True, copy_sig=True):
        """Add the test repository to the to the chroot."""
        return self.add_repository(os.path.join(get_tests_dir(), "repo"),
                                   copy_list, copy_sig)

    def add_cdrom_repository(self):
        """Emulate a repository on removable device."""
        # Create the content of a fake cdrom
        media_path = os.path.join(self.path, "tmp/fake-cdrom")
        # The cdom gets identified by the info file
        os.makedirs(os.path.join(media_path, ".disk"))
        with open(os.path.join(media_path, ".disk/info"), "w") as info:
            info.write("This is a fake CDROM")
        # Copy the test repository "on" the cdrom
        shutil.copytree(os.path.join(get_tests_dir(), "repo"),
                        os.path.join(media_path, "repo"))

        # Call apt-cdrom add
        mount_point = self.mount_cdrom()
        os.system("apt-cdrom add -m -d %s "
                  "-o 'Debug::Acquire::cdrom'=True "
                  "-o 'Acquire::cdrom::AutoDetect'=False "
                  "-o 'Dir'=%s" % (mount_point, self.path))
        self.unmount_cdrom()

        config_path = os.path.join(self.path, "etc/apt/apt.conf.d/11cdrom")
        with open(config_path, "w") as cnf:
            cnf.write('Debug::Acquire::cdrom True;\n'
                      'Acquire::cdrom::AutoDetect False;\n'
                      'Acquire::cdrom::NoMount True;\n'
                      'Acquire::cdrom::mount "%s";' % mount_point)

    def mount_cdrom(self):
        """Copy the repo information to the CDROM mount point."""
        mount_point = os.path.join(self.path, "media/cdrom")
        os.symlink(os.path.join(self.path, "tmp/fake-cdrom"), mount_point)
        return mount_point

    def unmount_cdrom(self):
        """Remove all files from the mount point."""
        os.unlink(os.path.join(self.path, "media/cdrom"))

    def add_repository(self, path, copy_list=True, copy_sig=True):
        """Add a sources.list entry to the chroot."""
        # Add a sources list
        lst_path = os.path.join(self.path, "etc/apt/sources.list")
        with open(lst_path, "w") as lst_file:
            lst_file.write("deb file://%s ./ # Test repository" % path)
        if copy_list:
            filename = apt_pkg.uri_to_filename("file://%s/." % path)
            shutil.copy(os.path.join(path, "Packages"),
                        "%s/var/lib/apt/lists/%s_Packages" % (self.path,
                                                              filename))
            if os.path.exists(os.path.join(path, "Release")):
                shutil.copy(os.path.join(path, "Release"),
                            "%s/var/lib/apt/lists/%s_Release" % (self.path,
                                                                 filename))
            if copy_sig and os.path.exists(os.path.join(path, "Release.gpg")):
                shutil.copy(os.path.join(path, "Release.gpg"),
                            "%s/var/lib/apt/lists/%s_Release.gpg" % (self.path,
                                                                     filename))


class AptKitTestCase(unittest.TestCase):

    @classmethod
    def setupClass(cls):
        # Start with a clean APT configuration to remove changes
        # of previous tests
        for key in set([key.split("::")[0] for key in apt_pkg.config.keys()]):
            apt_pkg.config.clear(key)
        apt_pkg.init_config()

    def start_fake_polkitd(self, options="all"):
        """Start a fake PolicyKit daemon.

        :param allowed_actions: comma separated list of allowed actions.
                                Defaults to all
        """
        try:
            env = os.environ.copy()
            env["DBUS_SYSTEM_BUS_ADDRESS"] = self.dbus_address
        except AttributeError:
            env = None
        dir = get_tests_dir()
        proc = subprocess.Popen([os.path.join(dir, "fake-polkitd.py"),
                                "--allowed-actions", options],
                                env=env)
        self.addCleanup(self._kill_process, proc)
        return proc

    def start_session_aptk(self, chroot="/", debug=True):
        """Start an aptkit which listens on the session D-Bus.

        :param chroot: path to the chroot
        """
        env = os.environ.copy()
        try:
            env["DBUS_SYSTEM_BUS_ADDRESS"] = self.dbus_address
        except AttributeError:
            pass
        try:
            env.pop("http_proxy")  # Unset a local proxy, see LP #1050799
        except KeyError:
            pass
        dir = get_tests_dir()
        if dir == "/usr/share/aptkit/tests":
            path = "/usr/sbin/aptk"
        else:
            path = os.path.join(dir, "../aptk")
        cmd = ["python3", path, "--disable-plugins",
               "--chroot", chroot]
        if debug:
            cmd.append("--debug")
        proc = subprocess.Popen(cmd, env=env)
        self.addCleanup(self._kill_process, proc)
        return proc

    def start_dbus_daemon(self):
        """Start a private D-Bus daemon and return its process and address."""
        proc, dbus_address = start_dbus_daemon()
        self.addCleanup(self._kill_process, proc)
        self.dbus_address = dbus_address

    def start_keyserver(self, filename=None):
        """Start a fake keyserver on hkp://localhost:19191

        Keyword arguments:
        filename -- Optional path to a GnuPG pulic key file which should
            be returned by lookups. By default the key of the test repo
            is used.
        """
        dir = tempfile.mkdtemp(prefix="keyserver-test-")
        self.addCleanup(shutil.rmtree, dir)
        os.mkdir(os.path.join(dir, "pks"))
        if filename is None:
            filename = os.path.join(get_tests_dir(), "repo/glatzor.gpg")
        shutil.copy(filename, os.path.join(dir, "pks", "lookup"))

        pid = os.fork()
        if pid == 0:
            # quiesce server log
            os.dup2(os.open('/dev/null', os.O_WRONLY), sys.stderr.fileno())
            os.chdir(dir)
            httpd = HTTPServer(('localhost', 19191), HTTPRequestHandler)
            httpd.serve_forever()
            os._exit(0)
        else:
            self.addCleanup(self._kill_pid, pid)

        # wait a bit until server is ready
        time.sleep(0.5)

    def _kill_pid(self, pid):
        os.kill(pid, 15)
        os.wait()

    def _kill_process(self, proc):
        proc.kill()
        proc.wait()


def get_tests_dir():
    """Return the absolute path to the tests directory."""
    # Try to detect a relative tests dir if we are running from the source
    # directory
    try:
        path = inspect.getsourcefile(sys.modules["aptkit.test"])
    except KeyError:
        path = inspect.getsourcefile(inspect.currentframe())
    path = os.path.realpath(path)
    relative_path = os.path.join(os.path.dirname(path), "../tests")
    if os.path.exists(os.path.join(relative_path, "repo/Packages")):
        return os.path.normpath(relative_path)
    # Fallback to an absolute path
    elif os.path.exists("/usr/share/aptkit/tests/repo/Packages"):
        return "/usr/share/aptkit/tests"
    else:
        raise Exception("Could not find tests direcotry")


def start_dbus_daemon():
    """Start a private D-Bus daemon and return its process and address."""
    config_path = os.path.join(get_tests_dir(), "dbus.conf")
    proc = subprocess.Popen(["dbus-daemon", "--nofork",
                             "--print-address", "--config-file",
                             config_path],
                            stdout=subprocess.PIPE)
    output = proc.stdout.readline().strip()
    if PY3K:
        dbus_address = output.decode()
    else:
        dbus_address = output
    return proc, dbus_address


# vim: ts=4 et sts=4
