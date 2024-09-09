#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests if we can handle different encodings well."""

import locale
import logging
import os
import sys
import unittest

from aptkit import core, enums, test, errors, utils

DEBUG = True

if sys.version >= '3':
    unicode = str


class GettextTest(test.AptKitTestCase):

    """Regression test for LP: #768691 and LP: #926340

    The gettext.translation.gettext() method returns a string in Python 2.
    If we try to perform a string format operation, Python wants to convert
    string to unicode. If the daemon is running with a different
    default encoding as the translated message this results in an error.
    By defaulf aptkit runs as C if activated by D-Bus.
    """

    def setUp(self):
        # Use the mo files from the build
        local_mo_files = os.path.join(test.get_tests_dir(),
                                      "../build/mo")
        if not os.path.isdir(local_mo_files):
            self.skipTest("Please run setup.py build before since local mo "
                          "files are required. Run python setup.py build_i18n")
        core.gettext._default_localedir = local_mo_files

        self.trans = core.Transaction(None, enums.ROLE_FIX_BROKEN_DEPENDS,
                                      None, os.getpid(), os.getuid(),
                                      sys.argv[0], "org.debian.aptkit.test",
                                      connect=False)
        self.codes = utils.IsoCodes("iso_639", tag="iso_639_1_code",
                                    fallback_tag="iso_639_2T_code")

    def test(self):
        """Test if the installation of an unauthenticated packages fails
        if simulate hasn't been called explicitly before.
        """
        self.trans._set_locale("de_DE.UTF-8")
        ret = self.trans.gettext("CD/DVD '%s' is required")
        self.assertTrue(isinstance(ret, unicode))
        error = errors.TransactionFailed(enums.ERROR_NO_PACKAGE,
                                         "CD/DVD '%s' is required", "lala")
        self.trans.error = error

        utils.gettext._default_localedir = "/usr/share/locale"
        lang = self.codes.get_localised_name("en", "ru.UTF-8")
        self.assertTrue(isinstance(lang, unicode))

if __name__ == "__main__":
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    unittest.main()

# vim: ts=4 et sts=4
