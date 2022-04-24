#!/usr/bin/python3
"""Fake a PolicyKit daemon."""

from optparse import OptionParser
import sys

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

# Setup the DBus main loop
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)


class FakePolicyKitDaemon(dbus.service.Object):

    def __init__(self, allowed_actions):
        self.allowed_actions = allowed_actions
        bus_name = dbus.service.BusName("org.freedesktop.PolicyKit1",
                                        dbus.SystemBus(),
                                        do_not_queue=True)
        dbus.service.Object.__init__(self, bus_name,
                                     "/org/freedesktop/PolicyKit1/Authority")
        self.loop = GLib.MainLoop()

    def run(self):
        self.loop.run()

    @dbus.service.method("org.freedesktop.PolicyKit1.Authority",
                         in_signature='(sa{sv})sa{ss}us',
                         out_signature='(bba{ss})')
    def CheckAuthorization(self, subject, action_id, details, flags,
                           cancellation_id):
        if "all" in self.allowed_actions:
            allowed = True
        else:
            allowed = action_id in self.allowed_actions
        challenged = False
        details = {"test": "test"}
        return (allowed, challenged, details)

    @dbus.service.method("org.freedesktop.PolicyKit1.Authority",
                         in_signature='', out_signature='')
    def Quit(self):
        GLib.idle_add(self._quit)

    def _quit(self):
        self.loop.quit()
        sys.exit()


def main():
    parser = OptionParser()
    parser.add_option("-a", "--allowed-actions",
                      default="", action="store", type="string",
                      dest="allowed_actions",
                      help="Comma separated list of allowed action ids")
    options, args = parser.parse_args()
    polkitd = FakePolicyKitDaemon(options.allowed_actions.split(","))
    polkitd.run()

if __name__ == "__main__":
    main()
