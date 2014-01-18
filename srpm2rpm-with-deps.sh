#!/usr/bin/env sh
# Build RPMs from a SRPM using given dependencies.
# Usage: ./srpm2rpm-with-deps.sh SRPM_PATH MOCK_CFG [DEP_PKG...]
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

mock --quiet --root="$2" --init

# Install dependencies.
if [ $# -gt 2 ]; then
	mock --quiet --root="$2" --install ${*:3};
fi

# Build RPM.
mock --quiet --root="$2" --no-clean "$1"