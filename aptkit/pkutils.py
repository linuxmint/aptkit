# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides helper functions for the PackageKit layer

Copyright (C) 2007 Ali Sabil <ali.sabil@gmail.com>
Copyright (C) 2007 Tom Parker <palfrey@tevp.net>
Copyright (C) 2008-2013 Sebastian Heinlein <glatzor@ubuntu.com>

Licensed under the GNU General Public License Version 2

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = "Sebastian Heinlein <devel@glatzor.de>"


def bitfield_summarize(*enums):
    """Return the bitfield with the given PackageKit enums."""
    field = 0
    for enum in enums:
        field |= 2 ** int(enum)
    return field


def bitfield_add(field, enum):
    """Add a PackageKit enum to a given field"""
    field |= 2 ** int(enum)
    return field


def bitfield_remove(field, enum):
    """Remove a PackageKit enum to a given field"""
    field = field ^ 2 ** int(enum)
    return field


def bitfield_contains(field, enum):
    """Return True if a bitfield contains the given PackageKit enum"""
    return field & 2 ** int(enum)


# vim: ts=4 et sts=4
