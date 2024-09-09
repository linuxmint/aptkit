#!/usr/bin/env python3

"""Test gtk3widgets.py."""

import os
import codecs
import shutil
import tempfile
import unittest

from aptkit.gtk3widgets import DiffView


class TestLP1120322(unittest.TestCase):

    def setUp(self):
        tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tempdir)
        self.a = os.path.join(tempdir, 'a.txt')
        self.b = os.path.join(tempdir, 'b.txt')
        with codecs.open(self.a, 'w', encoding='utf-8') as f:
            f.write('one\n')
        with codecs.open(self.b, 'w', encoding='utf-8') as f:
            f.write('onee\n')

    def test_lp_1120322(self):
        # UnboundLocalError when the diff is one line long.
        dv = DiffView()
        # This simply should not traceback.
        dv.show_diff(self.a, self.b)


class TestGoodPath(unittest.TestCase):

    def setUp(self):
        tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tempdir)
        self.a = os.path.join(tempdir, 'a.txt')
        self.b = os.path.join(tempdir, 'b.txt')
        with codecs.open(self.a, 'w', encoding='utf-8') as f:
            f.write('one\ntwo\n')
        with codecs.open(self.b, 'w', encoding='utf-8') as f:
            f.write('one\ntoo\n')

    def test_lp_1120322(self):
        # UnboundLocalError when the diff is multiple lines long.
        dv = DiffView()
        # This simply should not traceback.
        dv.show_diff(self.a, self.b)
