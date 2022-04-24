#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Provides unit tests for the APT configuration file parser"""
# Copyright (C) 2010 Sebastian Heinlein <devel@glatzor.de>
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

import os
import sys
import unittest

import apt_pkg

from aptdaemon.config import ConfigWriter


class ConfigurationParserTestCase(unittest.TestCase):

    """Test suite for the configuration parser."""

    def setUp(self):
        self.parser = ConfigWriter()

    def test_comment_in_value(self):
        """ ensure that comment strings in values are parsed correctly """
        s = """// Server information for apt-changelog
        APT {
         Changelogs { # bar
          Server "http://changelogs.ubuntu.com/changelogs"; // foo
         }
        }
        """
        cf = self.parser.parse(s.split("\n"))
        self.assertEqual(cf["apt::changelogs::server"].string,
                         "http://changelogs.ubuntu.com/changelogs")

    def test_multi_line_comments(self):
        s = """/*
 * APT configuration file for Zope Debian packages.
 */

DPkg {
    Post-Invoke {"which dzhandle";};
}
        """
        cf = self.parser.parse(s.split("\n"))
        self.assertEqual(cf["dpkg::post-invoke"][0].string, "which dzhandle")

    def test_(self):
        config = {}
        config_check = {}

        for filename in os.listdir("/etc/apt/apt.conf.d"):
            path = "/etc/apt/apt.conf.d/%s" % filename
            config_apt = apt_pkg.Configuration()
            with open(path, "r") as fd:
                apt_pkg.read_config_file(config_apt, path)
                config = self.parser.parse(fd.readlines())
            for key in config_apt.keys():
                if key.endswith("::"):
                    key = key[:-2]
                    value_list_apt = config_apt.value_list(key)
                    if value_list_apt:
                        value_list = [val.string for val in
                                      config[key.lower()]]
                        self.assertTrue(value_list_apt == value_list,
                                        "%s: %s != %s" % (key, value_list_apt,
                                                          value_list))
                else:
                    value_apt = config_apt[key]
                    if value_apt:
                        self.assertTrue(
                            value_apt == config[key.lower()].string)


@unittest.skipIf(sys.version_info.major < 3, "Only Python3")
def setUp():
    pass

if __name__ == "__main__":
    unittest.main()

# vim: ts=4 et sts=4
