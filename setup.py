#!/usr/bin/env python

# Work around "TypeError: 'NoneType' object is not callable"
# during `python setup.py test`
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html
import multiprocessing
multiprocessing  # pyflakes


import glob
import os
import sys
from setuptools import *

from DistUtilsExtra.command import (
    build_extra,
    build_i18n,
)

import aptkit

# The transaction class has got it's own gettext translation
# Don't set bug-contact in setup.cfg since p-d-u-e will overwrite
# XGETTEXT_ARGS otherwise.
os.environ["XGETTEXT_ARGS"] = "--keyword=self.trans.gettext"

setup(name="aptkit",
      version=aptkit.__version__,
      description="DBus driven daemon for APT",
      author="Sebastian Heinlein",
      author_email="devel@glatzor.de",
      packages=["aptkit", "aptkit.worker"],
      scripts=["aptk", "aptkcon"],
      test_suite="nose.collector",
      license="GNU LGPL",
      keywords="apt package manager deb dbus d-bus debian ubuntu dpkg",
      cmdclass={"build": build_extra.build_extra,
                "build_i18n": build_i18n.build_i18n},
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Intended Audience :: System Administrators",
                   "License :: OSI Approved :: GNU Library or Lesser General " \
                       "Public License (LGPL)",
                   "Programming Language :: Python :: 2.6",
                   "Topic :: System :: Systems Administration",
                   "Topic :: System :: Software Distribution"],
      url="http://launchpad.net/sessioninstaller",
      data_files=[("../etc/dbus-1/system.d/",
                   ["data/org.debian.aptkit.conf",
                    "data/org.freedesktop.PackageKit-aptk.conf"]),
                  ("../etc/apt/apt.conf.d/",
                   ["data/20aptkit"]),
                  ("share/apport/package-hooks",
                   ["apport/aptkit.py"]),
                  ("share/dbus-1/system-services/",
                   ["data/org.debian.aptkit.service",
                    "data/org.freedesktop.PackageKit.service"]),
                  ("share/man/man1",
                   ["doc/aptk.1", "doc/aptkcon.1"]),
                  ("share/man/man7",
                   ["doc/org.debian.aptkit.7",
                    "doc/org.debian.aptkit.transaction.7"]),
                  ],
      platforms="posix",
      )
