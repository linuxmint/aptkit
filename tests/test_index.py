#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test index handling."""

import os.path

import apt
import apt_pkg
import unittest

import aptkit.test


class IndexRaceTest(unittest.TestCase):

    """If the indexes are deleted or manipulated at the time
    apt.Cache.required_download was called we get the following error:
    SystemError: I wasn't able to locate file for the XXX package.
    This might mean you need to manually fix this package.

    See lp:#659438
    """

    def setUp(self):
        self.chroot = aptkit.test.Chroot()
        self.chroot.setup()
        self.chroot.add_test_repository()
        # Check if installing an uninstalled package works
        self.cache = apt.Cache(rootdir=self.chroot.path)
        self.cache["silly-base"].mark_install()
        self.assertEqual(self.cache.required_download, 0)
        self.cache.clear()

    def test(self):
        lists_path = apt_pkg.config.find_dir("Dir::State::Lists")
        for file_name in os.listdir(lists_path):
            if file_name.endswith("Packages"):
                os.remove(os.path.join(lists_path, file_name))
        self.cache["silly-base"].mark_install()
        self.assertRaises(SystemError,
                          lambda: self.cache.required_download)
#        self.cache.required_download


if __name__ == "__main__":
    unittest.main()

# vim: ts=4 et sts=4
