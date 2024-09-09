#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests the debconf forwarding"""
import unittest
from gi.repository import GLib

from aptkit import enums, client

DEBUG = False


class TransChainTest(unittest.TestCase):

    """These tests require an aptkit running with the dummy worker:
    # sudo aptk -td --dummy
    """

    def setUp(self):
        self.loop = GLib.MainLoop()
        self.client = client.AptClient()

    def _test_working(self):
        def on_finished(trans, exit):
            self.loop.quit()
        trans1 = self.client.upgrade_packages(["huhu"])
        trans2 = self.client.upgrade_packages(["lala"])
        trans3 = self.client.upgrade_packages(["huhu"])
        trans2.run_after(trans1)
        trans3.run_after(trans2)
        trans1.run()
        trans3.connect("finished", on_finished)
        self.loop.run()
        self.assertTrue(trans1.exit == enums.EXIT_SUCCESS)
        self.assertTrue(trans2.exit == enums.EXIT_SUCCESS)
        self.assertTrue(trans3.exit == enums.EXIT_SUCCESS)

    def _test_fail_after(self):
        def on_finished(trans, exit):
            self.loop.quit()
        trans1 = self.client.update_cache()
        trans2 = self.client.upgrade_packages(["huhululu"])
        trans3 = self.client.upgrade_packages(["huhululu"])
        trans2.run_after(trans1)
        trans3.run_after(trans2)
        trans1.run()
        trans3.connect("finished", on_finished)
        self.loop.run()
        self.assertTrue(trans1.exit == enums.EXIT_FAILED)
        self.assertTrue(trans2.exit == enums.EXIT_PREVIOUS_FAILED)
        self.assertTrue(trans3.exit == enums.EXIT_PREVIOUS_FAILED)


if __name__ == "__main__":
    import logging
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
