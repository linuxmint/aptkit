#!/bin/bash
# release.sh - Prepare a release and upload it

set -e

USAGE="USAGE: release.sh VERSION"

VERSION=$1
VERSION_TAG=$(echo "$VERSION" | perl -pi -e "s/\./_/g")
TARBALL=dist/aptdaemon-$VERSION.tar.gz
DATE=$(LC_TIME=C date +%c)

if [ -z "$(bzr status | grep -v shelve)" ]; then
	echo "ERROR: Uncommitted changes, aborting" >&2
        exit 1
fi


if [ ! $(echo $VERSION | egrep "^[0-9\.]+$") ]; then
	echo "ERROR: Specify a vaild version number as argument" >&2
	echo $USAGE
	exit 1
fi


if [ -e $TARBALL.gz ]; then
	echo "ERROR: Tarball already exists!" >&2
	echo $USAGE
	exit 1
fi

echo "Preparing $VERSION release..."

# Run the test suite
# python3 setup.py test
# python setup.py test

bzr clean-tree --ignored

# Set the version number
sed -i "1s/.*/VERSION $VERSION - released on $DATE/" NEWS
sed -i "s/^\(__version__ = \).*/\1'$VERSION'/" aptdaemon/__init__.py

# Create the tarball
bzr inventory --kind file | sed "s/^/include /" > MANIFEST.in
bzr log --gnu-changelog -n0 > ChangeLog
echo "include ChangeLog" >> MANIFEST.in

read -p "Do you want to publish the release? (y/N) " PUBLISH
echo ""

if [ "$PUBLISH" != "y" ]; then
	echo "Cancelling..."
	exit 1
fi

echo "Uploading to Python Package Index..."
python3 setup.py sdist upload

gpg --armor --sign --detach-sig $TARBALL

echo "Commiting to VCS repository..."
bzr commit NEWS aptdaemon/__init__.py -m "Release version $VERSION"
bzr tag APTDAEMON_$VERSION_TAG

echo "Uploading to Launchpad..."
lp-project-upload aptdaemon $VERSION $TARBALL
