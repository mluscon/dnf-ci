#!/usr/bin/env sh
# Convert the libcomps GIT repository into a source archive and make the SPEC file.
# Usage: ./libcomps-git2src-make-spec-in-mock.sh CFG_DIR MOCK_CFG
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

MOCK_DIR=/tmp/libcomps-git2src-make-spec-in-mock
/usr/bin/mock --quiet --configdir="$1" --root="$2" --chroot "rm --recursive --force '$MOCK_DIR'"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --copyin . "$MOCK_DIR"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --chroot "chown --recursive :mockbuild '$MOCK_DIR'"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --install python git

/usr/bin/mock --quiet --configdir="$1" --root="$2" --unpriv --shell "cd '$MOCK_DIR' && ./build_prep.py"; EXIT=$?

TMP_DIR=/tmp
TMP_HOME="$TMP_DIR"/libcomps-git2src-make-spec-in-mock
mkdir --parents "$TMP_DIR"
chmod a+rwx "$TMP_DIR"
rm --recursive --force "$TMP_HOME"
/usr/bin/mock --quiet --configdir="$1" --root="$2" --copyout "$MOCK_DIR" "$TMP_HOME"
mv "$TMP_HOME"/libcomps-*.tar.gz .
mv "$TMP_HOME/libcomps.spec" .
exit $EXIT
