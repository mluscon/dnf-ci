#!/usr/bin/env sh
# Build the libcomps RPMs from the GIT repository.
# Usage: ./libcomps-git2rpm.sh CFG_DIR MOCK_CFG BUILD_NUMBER [DEP_PKG...]
#
# Copyright (C) 2014  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.

# Convert the GIT repository to a source archive and make the SPEC file.
python --version >>/dev/null 2>&1; PYTHON_EXIT=$?
case "$PYTHON_EXIT" in
	# Python is installed.
	0) 		IS_PYTHON=0;;
	# Python is not installed.
	127)	echo "WARNING: python is not installed" 1>&2
			IS_PYTHON=1;;
esac
git --version >>/dev/null 2>&1; GIT_EXIT=$?
case "$GIT_EXIT" in
	# GIT is installed.
	0) 		IS_GIT=0;;
	# GIT is not installed.
	127)	echo "WARNING: git is not installed" 1>&2
			IS_GIT=1;;
esac
if [ $(($IS_PYTHON + $IS_GIT)) -eq 0 ]; then
	./build_prep.py;
else
	echo "WARNING: => using mock" 1>&2
	./libcomps-git2src-make-spec-in-mock.sh "$1" "$2"
fi
SRC_DIR=.
SPEC_PATH=libcomps.spec

# Edit the SPEC file.
./libcomps-edit-spec.sh "$SPEC_PATH" "$3"

# Build the SRPM.
SRPM_DIR=.
SRPM_GLOB="$SRPM_DIR"/libcomps-*.src.rpm
rm --force "$SRPM_DIR"/$SRPM_GLOB
/usr/bin/mock --quiet --configdir="$1" --root="$2" --buildsrpm --spec "$SPEC_PATH" --sources "$SRC_DIR"
mv "/var/lib/mock/$2/result"/$SRPM_GLOB "$SRPM_DIR"

# Build the RPMs.
./srpm2rpm-with-deps.sh "$SRPM_DIR"/$SRPM_GLOB "$1" "$2" ${*:4}
