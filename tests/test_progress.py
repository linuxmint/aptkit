#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the debconf forwarding"""

import apt
import logging
import mock
import sys
import unittest

import aptkit.test
from aptkit.progress import DaemonOpenProgress


class TestProgress(unittest.TestCase):

    def setUp(self):
        self.chroot = aptkit.test.Chroot()
        self.chroot.setup()
        self.addCleanup(self.chroot.remove)

    def test_open_progress(self):
        transaction = mock.Mock()
        begin = 0
        end = 5
        d = DaemonOpenProgress(transaction, begin=begin, end=end)
        # simulate cache open (c = apt.Cache(d)))
        for j in range(4):
            for i in range(0, 100, 10):
                d.update(i)
                self.assertTrue(d.progress >= begin)
                self.assertTrue(d.progress <= end)
            d.done()
        # ensure we use the full range
        self.assertEqual(d.progress, end)

    def test_open_progress_real_cache(self):
        transaction = mock.Mock()
        begin = 0
        end = 5
        d = DaemonOpenProgress(transaction, begin=begin, end=end)
        c = apt.Cache(d)
        # ensure we use the full range
        self.assertEqual(d.progress, end)


@unittest.skipIf(sys.version_info.major < 3, "Python 3 only")
def setUp():
    pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
