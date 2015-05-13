#!/usr/bin/env sh
# Build the librepo RPMs from the GIT repository.
# Usage: ./librepo-git2rpm-in-mock.sh CFG_DIR MOCK_CFG TAG_RELEASE [DEP_PKG...]
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

MOCK_DIR=/tmp/librepo-git2rpm
/usr/bin/mock --quiet --configdir="$1" --root="$2" --chroot "rm --recursive --force '$MOCK_DIR'"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --copyin . "$MOCK_DIR"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --chroot "chown --recursive :mockbuild '$MOCK_DIR'"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --chroot "chmod --recursive +w '$MOCK_DIR'"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --install wget yum git check-devel cmake expat-devel gcc glib2-devel gpgme-devel libattr-devel libcurl-devel openssl-devel python-devel python3-devel pygpgme python3-pygpgme python-flask python3-flask python-nose python3-nose pyxattr python3-pyxattr doxygen python-sphinx python3-sphinx
/usr/bin/mock --quiet --configdir="$1" --root="$2" --chroot "ln --symbolic --force /builddir/build \"\$HOME/rpmbuild\""

# Install dependencies.
if [ $# -gt 2 ]; then
	/usr/bin/mock --quiet --configdir="$1" --root="$2" --install ${*:4};
fi

# Build RPM.
/usr/bin/mock --quiet --configdir="$1" --root="$2" --unpriv --shell "cd '$MOCK_DIR' && ./librepo-git2rpm.sh '$3'"; EXIT=$?

TMP_DIR=/tmp/librepo-git2rpm
TMP_HOME="$TMP_DIR"/home
TMP_RPMS="$TMP_DIR"/RPMS
RPMS_DIR="$HOME/rpmbuild/RPMS"
mkdir --parents "$TMP_DIR"
chmod a+rwx "$TMP_DIR"
rm --recursive --force "$TMP_HOME" "$TMP_RPMS"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --copyout "$MOCK_DIR" "$TMP_HOME"
mv "$TMP_HOME"/librepo-*.src.rpm .
/usr/bin/mock --quiet --configdir="$1" --root="$2" --copyout "/builddir/build/RPMS" "$TMP_RPMS"
mkdir --parents "$RPMS_DIR"
mv "$TMP_RPMS"/*librepo-*.rpm "$RPMS_DIR"
exit $EXIT
