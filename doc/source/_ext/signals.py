"""Adds a new directive signal for GObject signals"""

import re

from sphinx import addnodes

signal_re = re.compile(r"([a-zA-Z-]+)\s->(.*)")

def parse_signal(env, sig, signode):
    match = signal_re.match(sig)
    if not match:
        signode += addnodes.desc_name(sig, sig)
        return sig
    name, args = match.groups()
    signode += addnodes.desc_name(name, name)
    signode += addnodes.desc_returns(args.strip(), args.strip())
    return name

def setup(app):
    app.add_description_unit("signal", "sig", "pair: %s; signal", parse_signal)
