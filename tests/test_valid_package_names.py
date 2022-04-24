#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test index handling."""

import sys
import unittest

import apt
import mock

import aptdaemon.core
import aptdaemon.errors


class TestValidPacakgeNames(unittest.TestCase):

    """Test the code that verifies for valid package names
    """

    def setUp(self):
        self.cache = apt.Cache()
        opt = mock.Mock()
        opt.dummy = True
        self.daemon = aptdaemon.core.AptDaemon(opt, connect=False)

    def test_valid_package_names(self):
        # ensure that the code raises on invalid ones, note that we
        # test each item individually instead of the list because each
        # needs to raise
        for invalid in [
                "foo_bar", "äää", "i space", "a", "+invalidstart", "noUpper",
                "foo=", "foo=", "foo=a", "foo=0 space"
                "foo/", "foo/ space"]:
            with self.assertRaises(aptdaemon.errors.AptDaemonError):
                self.daemon._check_package_names([invalid])

        # check some simple good cases
        for pkgname in ["apt", "apt/unstable", "apt=0.3.2", "apt:i386",
                        "apt+:i386/unstable", "apt+:amd64=0.3.2"]:
            self.daemon._check_package_names([pkgname])

        # ensure the code does not wrongly label valid packages as
        # invalid, _check_package_names will raise on error
        for pkg in self.cache:
            self.daemon._check_package_names([pkg.name])

        # test again, this time with version number
        for pkg in self.cache:
            if not pkg.candidate:
                continue
            self.daemon._check_package_names(
                ["%s=%s" % (pkg.name, pkg.candidate.version)])

        # test again, this time with release origin
        for pkg in self.cache:
            if not pkg.candidate:
                continue
            archive = pkg.candidate.origins[0].archive
            if archive:
                self.daemon._check_package_names(["%s/%s" % (pkg.name,
                                                             archive)])


@unittest.skipIf(sys.version_info.major < 3, "Python 3 only")
def setUp():
    pass

if __name__ == "__main__":
    unittest.main()

# vim: ts=4 et sts=4
