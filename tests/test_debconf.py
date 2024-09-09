#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the debconf forwarding"""

import logging
import os
import subprocess
import sys
import tempfile
import unittest

import apt_pkg
from gi.repository import GLib

from aptkit import test
from aptkit.debconf import DebconfProxy

DEBUG = False


class DebconfTestBasic(unittest.TestCase):

    def _stop(self):
        self.proxy.stop()
        self.loop.quit()

    def setUp(self):
        self.loop = GLib.MainLoop()
        self.debconf_socket_path = tempfile.mktemp(prefix="debconf-socket-")
        self._set_input_value()
        self.proxy = DebconfProxy("editor", self.debconf_socket_path)
        self.proxy.start()

    def _set_input_value(self, template="aptkit/test", value="lalelu"):
        os.environ["DEBIAN_PRIORITY"] = "high"
        os.environ["EDITOR"] = "sed -ie 's/\\(%s=\\).*/\\1\\\"%s\\\"/i'" % \
                               (template.replace("/", "\\/"), value)

    def _spawn_config_script(self, config_db_path, command=None):
        if command is None:
            command = [os.path.join(test.get_tests_dir(),
                                    "debconf/aptkit.config")]
        env = {}
        env["DEBCONF_DB_REPLACE"] = "File{%s}" % config_db_path
        env["DEBIAN_FRONTEND"] = "passthrough"
        env["DEBCONF_PIPE"] = self.debconf_socket_path
        if DEBUG:
            env["DEBCONF_DEBUG"] = ".*"
        env_str = ["%s=%s" % (key, val) for key, val in env.items()]

        proc = subprocess.Popen(command, env=env)
        return proc

    def testBasic(self):
        def config_done(pid, cond):
            self.assertEqual(cond, 0,
                             "Config script failed: %s" % os.WEXITSTATUS(cond))
            self._stop()
        debconf_db_path = tempfile.mktemp(suffix=".dat",
                                          prefix="config-basic-")
        proc = self._spawn_config_script(debconf_db_path)
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, proc.pid, config_done)
        self.loop.run()
        # Check the results
        self._check_value(debconf_db_path)

    @unittest.skipIf(sys.version_info.major < 3 and "nose" in sys.modules,
                     "For unknown reasons lets other tests fail "
                     "(test_simulate) if performed under Python2 and nose")
    def testSerial(self):
        """Run several config scripts in a row."""
        def config_done(pid, cond):
            self.assertEqual(cond, 0,
                             "Config script failed: %s" % os.WEXITSTATUS(cond))
            self.config_scripts -= 1
            if self.config_scripts <= 0:
                self._stop()
            else:
                proc = self._spawn_config_script(debconf_db_path)
                GLib.child_watch_add(GLib.PRIORITY_DEFAULT,
                                     proc.pid, config_done)
        debconf_db_path = tempfile.mktemp(suffix=".dat", prefix="config-row-")
        self.config_scripts = 10
        proc = self._spawn_config_script(debconf_db_path)
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, proc.pid, config_done)
        self.loop.run()
        # Check the results
        self._check_value(debconf_db_path)

    def testRace(self):
        def config_done(pid, cond):
            self.assertEqual(cond, 0,
                             "Config script failed: %s" % os.WEXITSTATUS(cond))
            self.workers -= 1
            if self.workers <= 0:
                self._stop()
        debconf_dbs = []
        self.workers = 0
        for i in range(10):
            debconf_db_path = tempfile.mktemp(suffix=".dat",
                                              prefix="config-race-")
            proc = self._spawn_config_script(debconf_db_path)
            GLib.child_watch_add(GLib.PRIORITY_DEFAULT, proc.pid, config_done)
            debconf_dbs.append(debconf_db_path)
            self.workers += 1
        self.loop.run()
        # Check the results
        for db_path in debconf_dbs:
            self._check_value(db_path)

    def _check_value(self, db_path, template=None, value="lalelu"):
        with open(db_path) as db_file:
            for section in apt_pkg.TagFile(db_file):
                if template == section["Template"] or template is None:
                    self.assertEqual(section["Value"], value)
                    return
        os.remove(db_path)
        self.fail("Database doesn't contain any matching value or template")

    def tearDown(self):
        os.remove(self.debconf_socket_path)
        self.proxy = None
        self.loop.quit()
        self.loop = None


if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
