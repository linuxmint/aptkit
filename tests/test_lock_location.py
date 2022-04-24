#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests locking."""

import imp
import logging
import os
import subprocess
import sys
import unittest

DEBUG = False


class LockFileLocationTest(unittest.TestCase):

    def test_lock_file_location(self):
        """Make sure that the correct lock files are used."""
        # Make sure that the lock module is reloaded if called from
        # within a test suite (to ensure no stale apt_pkg.config values
        # hanging around)
        import aptdaemon.lock
        imp.reload(aptdaemon.lock)
        # the actual test
        self.assertEqual(aptdaemon.lock.status_lock.path,
                         os.path.join(os.path.dirname(self.STATUS_PATH),
                                      "lock"))
        self.assertEqual(aptdaemon.lock.lists_lock.path,
                         os.path.join(self.LISTS_PATH, "lock"))
        self.assertEqual(aptdaemon.lock.archive_lock.path,
                         os.path.join(self.ARCHIVES_PATH, "lock"))

    def setUp(self):
        """Extract the currently used pathes."""
        for var, lock in [("self.STATUS_PATH", "'dir::state::status'/f"),
                          ("self.LISTS_PATH", "'dir::state::lists'/d"),
                          ("self.ARCHIVES_PATH", "'dir::cache::archives'/d")]:
            cmd = subprocess.Popen("/usr/bin/apt-config shell %s %s" % (var,
                                                                        lock),
                                   shell=True, stdout=subprocess.PIPE)
            exec(cmd.communicate()[0])


@unittest.skipIf(sys.version_info.major < 3, "Only Python 3")
def setUp():
    pass

if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
