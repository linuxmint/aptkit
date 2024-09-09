#!/usr/bin/python

import dbus

from gi.repository import GLib

from aptkit.client import AptClient
from aptkit.defer import inline_callbacks
from aptkit import policykit1

loop = GLib.MainLoop()

def on_finished(trans, exit):
    loop.quit()
    print exit

@inline_callbacks
def main():
    repo = ["deb", "http://packages.glatzor.de/silly-packages", "sid", ["main"],
            "Silly packages", "silly.list"]
    aptclient = AptClient()
    bus = dbus.SystemBus()
    name = bus.get_unique_name()
    # high level auth
    try:
        # Preauthentication
        action = policykit1.PK_ACTION_INSTALL_PURCHASED_PACKAGES
        flags = policykit1.CHECK_AUTH_ALLOW_USER_INTERACTION
        yield policykit1.check_authorization_by_name(name, action, flags=flags)
        # Setting up transactions
        trans_add = yield aptclient.add_repository(*repo)
        trans_update = yield aptclient.update_cache("silly.list")
        trans_inst = yield aptclient.install_packages(["silly-base"])
        yield trans_inst.set_allow_unauthenticated(True)
        # Check when the last transaction was done
        trans_inst.connect("finished", on_finished)
        # Chaining transactions
        yield trans_update.run_after(trans_add)
        yield trans_inst.run_after(trans_update)
        yield trans_add.run()
    except Exception as error:
        print error
        loop.quit()

if __name__ == "__main__":
    main()
    loop.run()
