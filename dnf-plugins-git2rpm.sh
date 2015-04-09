#!/usr/bin/env sh
# Build the dnf plugins RPMs from the GIT repository.
# Usage: ./dnf-plugins-git2rpm.sh CFG_DIR MOCK_CFG BUILD_NUMBER [DEP_PKG...]
#
# Copyright (C) 2014-2015  Red Hat, Inc.
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

MOCK_DIR=/tmp/dnf-plugins-git2rpm
mock --quiet --configdir="$1" --root="$2" --init
mock --quiet --configdir="$1" --root="$2" --copyin . "$MOCK_DIR"
mock --quiet --configdir="$1" --root="$2" --chroot "chown --recursive :mockbuild '$MOCK_DIR'"
DEPS=(${*:4})
DEPS=(${DEPS[@]//dnf-yum-*})
mock --quiet --configdir="$1" --root="$2" --install git yum-utils tito ${DEPS[@]}

# Get GIT revision hash.
git --version >>/dev/null 2>&1; GIT_EXIT=$?
case "$GIT_EXIT" in
	# GIT is installed.
	0)	GITREV=$(git rev-parse HEAD);;
	# GIT is not installed.
	127)	echo "WARNING: git is not installed => using mock" 1>&2
		GITREV=$(mock --quiet --configdir="$1" --root="$2" --unpriv --chroot "git -C '$MOCK_DIR' rev-parse HEAD");;
esac

# Edit the SPEC file.
SPEC_PATH=dnf-plugins-core.spec
mock --quiet --configdir="$1" --root="$2" --chroot "cd $MOCK_DIR; ./dnf-plugins-edit-spec.sh '$SPEC_PATH' '$GITREV' '$3'; git config user.name 'dnf-plugins-git2rpm'; git config user.email 'dnf-ci'; git add '$SPEC_PATH'; git commit --message='Set a snapshot release.'"

# Build the RPMs.
mock --quiet --configdir="$1" --root="$2" --chroot "yum-builddep '$MOCK_DIR/$SPEC_PATH'"
mock --quiet --configdir="$1" --root="$2" --unpriv --chroot "cd $MOCK_DIR; tito build --rpm --test --no-cleanup"
