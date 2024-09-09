# AptKit

Aptkit allows to perform package management tasks in a background process
controlled by DBus. It is the continuation of aptdaemon which is not actively
maintained and only exists in Ubuntu.

Aptdaemon was greatly inspired by PackageKit, which doesn't support
essential features of apt by policy.

# TODO

- Add convenience functions from mintcommon
- Set up makepot and LP translations
- Reduce the scope by removing unnecessary features
- Add a downgrade function
- Remove apport support? (Ubuntu-specific)
- Add support for XApp Window Progress
- Clean up code and copyrights with a reuse.toml and debian/copyright
