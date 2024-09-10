# AptKit

Aptkit allows to perform package management tasks in a background process
controlled by DBus. It is the continuation of aptdaemon which is not actively
maintained and only exists in Ubuntu.

Aptdaemon was greatly inspired by PackageKit, which doesn't support
essential features of apt by policy.

# TRANSLATIONS

This project is translated on Launchpad at https://translations.launchpad.net/linuxmint/latest/+pots/aptkit.

Please do not make pull requests to modify `po/` files directly. These are overwritten when we import translations
from Launchpad.

# TODO

- Add convenience functions from mintcommon
- Reduce the scope by removing unnecessary features
- Add a downgrade function
- Add support for XApp Window Progress
- Clean up code and copyrights with a reuse.toml and debian/copyright
