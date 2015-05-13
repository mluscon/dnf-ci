#!/usr/bin/env sh
# Build RPMs of a tito-enabled project using given dependencies.
# Usage: ./tito2rpm-with-deps.sh MOCK_ARGS CFG_DIR MOCK_CFG [DEP_PKG...]
#
# Copyright (C) 2015  Red Hat, Inc.
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

/usr/bin/mock --quiet --configdir="$2" --root="$3" --init

# Install dependencies.
if [ $# -gt 3 ]; then
	/usr/bin/mock --quiet --configdir="$2" --root="$3" --install ${*:4};
fi

# Build RPM.
tito build --rpm --test --no-cleanup --builder=mock --arg=mock="$3" --arg="mock_config_dir=$2" --arg=mock_args="--no-clean $1"
