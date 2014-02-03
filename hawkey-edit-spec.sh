#!/usr/bin/env sh
# Edit the hawkey spec file.
# Usage: ./hawkey-edit-spec.sh SPEC_PATH GIT_REV BUILD_NUMBER
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

sed --in-place "s/%global gitrev [a-zA-Z0-9]\{7\}/%global gitrev $2/g" "$1"
if [ $3 -ne 0 ]; then
	sed --in-place "s/^\(Release:\s*\)[0-9]\+\(%{?dist}\)$/\199.$3.%(date +%%Y%%m%%d)git%{gitrev}\2/" "$1"
fi
