#!/usr/bin/env sh
# Test all projects and code using given configuration.
# Usage: ./all-test-git-in-mock.sh CFG_PATH BUILD_NUMBER SKIP_LINT
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

MOCK_CFG=$(basename "$1" | sed 's/.cfg$//')
RPMS_DIR=.
RPMS_SUFFIX=.rpm
echo "Testing all projects and code using $1..."

# Initialize the modified mock.
echo "Initializing the $MOCK_CFG mock..."
cp /etc/mock/site-defaults.cfg .
cp /etc/mock/logging.ini .
/usr/bin/mock --quiet --configdir=. --root="$MOCK_CFG" --init
echo "...initialization done."

# Build hawkey.
echo "Building hawkey RPMs from the GIT repository in $MOCK_CFG mock..."
cd hawkey
rm --force "/tmp/tito"/*hawkey-*"$RPMS_SUFFIX"
./hawkey-git2rpm.sh .. "$MOCK_CFG" "$2" "../$RPMS_DIR"/*"$RPMS_SUFFIX" > ../hawkey-build.log 2>&1; HAWKEY_EXIT=$?
mv "/tmp/tito"/*hawkey-*"$RPMS_SUFFIX" "../$RPMS_DIR"
cd ..
if [ $HAWKEY_EXIT -eq 0 ]; then
	echo "...build succeeded."
else
	echo "...build failed with $HAWKEY_EXIT."
fi

# Build librepo.
echo "Building librepo RPMs from the GIT repository in $MOCK_CFG mock..."
cd librepo
./librepo-git2rpm-in-mock.sh .. "$MOCK_CFG" "$2" "../$RPMS_DIR"/*"$RPMS_SUFFIX" > ../librepo-build.log 2>&1; LIBREPO_EXIT=$?
mv librepo-*.src"$RPMS_SUFFIX" "../$RPMS_DIR"
mv "$HOME/rpmbuild/RPMS"/*librepo-*"$RPMS_SUFFIX" "../$RPMS_DIR"
cd ..
if [ $LIBREPO_EXIT -eq 0 ]; then
	echo "...build succeeded."
else
	echo "...build failed with $LIBREPO_EXIT."
fi

# Build libcomps.
echo "Building libcomps RPMs from the GIT repository in $MOCK_CFG mock..."
cd libcomps
./libcomps-git2rpm.sh .. "$MOCK_CFG" "$2" "../$RPMS_DIR"/*"$RPMS_SUFFIX"; LIBCOMPS_EXIT=$?
mv "/var/lib/mock/$MOCK_CFG/result"/*libcomps-*"$RPMS_SUFFIX" "../$RPMS_DIR"
mv "/var/lib/mock/$MOCK_CFG/result/installed_pkgs" ../libcomps-installed_pkgs
mv "/var/lib/mock/$MOCK_CFG/result/build.log" ../libcomps-build.log
cd ..
if [ $LIBCOMPS_EXIT -eq 0 ]; then
	echo "...build succeeded."
else
	echo "...build failed with $LIBCOMPS_EXIT."
fi

# Build dnf.
echo "Building dnf RPMs from the GIT repository in $MOCK_CFG mock..."
#tito cleans the BUILD directory (see https://bugzilla.redhat.com/show_bug.cgi?id=1205744)
#DNF_BUILD2=dnf-build2
#DNF_BUILD3=dnf-build3
cd dnf
./dnf-git2rpm.sh .. "$MOCK_CFG" "$2" "../$RPMS_DIR"/*"$RPMS_SUFFIX" > ../dnf-build.log 2>&1; DNF_EXIT=$?
#rm --recursive --force "../$DNF_BUILD2" "../$DNF_BUILD3"
#mock --quiet --configdir=.. --root="$MOCK_CFG" --copyout /builddir/build/BUILD/dnf "../$DNF_BUILD2"
#mv "../$DNF_BUILD2/py3" "../$DNF_BUILD3"
/usr/bin/mock --quiet --configdir=.. --root="$MOCK_CFG" --copyout "/tmp/tito/*dnf-*$RPMS_SUFFIX" "../$RPMS_DIR"
cd ..
if [ $DNF_EXIT -eq 0 ]; then
	echo "...build succeeded."
else
	echo "...build failed with $DNF_EXIT."
fi

# Build dnf plugins.
echo "Building dnf plugins RPMs from the GIT repository in $MOCK_CFG mock..."
#tito cleans the BUILD directory (see https://bugzilla.redhat.com/show_bug.cgi?id=1205744)
#PLUGINS_BUILD=dnf-plugins-core-build
cd dnf-plugins-core
./dnf-plugins-git2rpm.sh .. "$MOCK_CFG" "$2" "../$RPMS_DIR"/*"$RPMS_SUFFIX" > ../dnf-plugins-core-build.log 2>&1; PLUGINS_EXIT=$?
#rm --recursive --force "../$PLUGINS_BUILD"
#mock --quiet --configdir=.. --root="$MOCK_CFG" --copyout /builddir/build/BUILD/dnf-plugins-core "../$PLUGINS_BUILD"
/usr/bin/mock --quiet --configdir=.. --root="$MOCK_CFG" --copyout "/tmp/tito/*dnf-plugins-core*$RPMS_SUFFIX" "../$RPMS_DIR"
cd ..
if [ $PLUGINS_EXIT -eq 0 ]; then
	echo "...build succeeded."
else
	echo "...build failed with $PLUGINS_EXIT."
fi

# Test builds.
echo "Running tests in $MOCK_CFG mock..."
/usr/bin/mock --quiet --configdir=. --root="$MOCK_CFG" --init
/usr/bin/mock --quiet --configdir=. --root="$MOCK_CFG" --install "$RPMS_DIR"/*"$RPMS_SUFFIX"
#cd "$DNF_BUILD2" # dnf python 2
#cp ../test-python-project.sh ../test-python2-code.sh .
DNF_TESTS2_EXIT=0
#../test-python-project-in-mock.sh 2.7 . .. "$MOCK_CFG" > ../dnf-python2-tests.log 2>&1; DNF_TESTS2_EXIT=$?
DNF_LINT2_EXIT=0
#../test-python2-code-in-mock.sh .. "$MOCK_CFG"; DNF_LINT2_EXIT=$?
#mv pep8.log ../dnf-python2-pep8.log
#sed --in-place "s,^\./\([^:]\+:[0-9]\+:.*\),dnf/\1," ../dnf-python2-pep8.log
#mv pyflakes.log ../dnf-python2-pyflakes.log
#sed --in-place "s,^\./\([^:]\+:[0-9]\+:.*\),dnf/\1," ../dnf-python2-pyflakes.log
#mv pylint.log ../dnf-python2-pylint.log
#sed --in-place "s,^[^:]\+:[0-9]\+:,dnf/\0," ../dnf-python2-pylint.log
#cd "../$DNF_BUILD3" # dnf python 3
#cp ../test-python-project.sh ../test-python3-code.sh .
DNF_TESTS3_EXIT=0
#../test-python-project-in-mock.sh 3.4 . .. "$MOCK_CFG" > ../dnf-python3-tests.log 2>&1; DNF_TESTS3_EXIT=$?
DNF_LINT3_EXIT=0
#../test-python3-code-in-mock.sh .. "$MOCK_CFG"; DNF_LINT3_EXIT=$?
#mv pep8.log ../dnf-python3-pep8.log
#sed --in-place "s,^\./\([^:]\+:[0-9]\+:.*\),dnf/\1," ../dnf-python3-pep8.log
#mv pyflakes.log ../dnf-python3-pyflakes.log
#sed --in-place "s,^\./\([^:]\+:[0-9]\+:.*\),dnf/\1," ../dnf-python3-pyflakes.log
#mv pylint.log ../dnf-python3-pylint.log
#sed --in-place "s,^[^:]\+:[0-9]\+:,dnf/\0," ../dnf-python3-pylint.log
#cd "../$PLUGINS_BUILD" # dnf-plugins-core python
#cp ../test-python-project.sh ../test-python2-code.sh ../test-python3-code.sh .
PLG_TESTS2_EXIT=0
#../test-python-project-in-mock.sh 2.7 plugins .. "$MOCK_CFG" > ../dnf-plugins-core-python2-tests.log 2>&1; PLG_TESTS2_EXIT=$?
PLG_TESTS3_EXIT=0
#../test-python-project-in-mock.sh 3.4 plugins .. "$MOCK_CFG" > ../dnf-plugins-core-python3-tests.log 2>&1; PLG_TESTS3_EXIT=$?
PLG_LINT2_EXIT=0
#../test-python2-code-in-mock.sh .. "$MOCK_CFG"; PLG_LINT2_EXIT=$?
#mv pep8.log ../dnf-plugins-core-python2-pep8.log
#sed --in-place "s,^\./\([^:]\+:[0-9]\+:.*\),dnf-plugins-core/\1," ../dnf-plugins-core-python2-pep8.log
#mv pyflakes.log ../dnf-plugins-core-python2-pyflakes.log
#sed --in-place "s,^\./\([^:]\+:[0-9]\+:.*\),dnf-plugins-core/\1," ../dnf-plugins-core-python2-pyflakes.log
#mv pylint.log ../dnf-plugins-core-python2-pylint.log
#sed --in-place "s,^[^:]\+:[0-9]\+:,dnf-plugins-core/\0," ../dnf-plugins-core-python2-pylint.log
PLG_LINT3_EXIT=0
#../test-python3-code-in-mock.sh .. "$MOCK_CFG"; PLG_LINT3_EXIT=$?
#mv pep8.log ../dnf-plugins-core-python3-pep8.log
#sed --in-place "s,^\./\([^:]\+:[0-9]\+:.*\),dnf-plugins-core/\1," ../dnf-plugins-core-python3-pep8.log
#mv pyflakes.log ../dnf-plugins-core-python3-pyflakes.log
#sed --in-place "s,^\./\([^:]\+:[0-9]\+:.*\),dnf-plugins-core/\1," ../dnf-plugins-core-python3-pyflakes.log
#mv pylint.log ../dnf-plugins-core-python3-pylint.log
#sed --in-place "s,^[^:]\+:[0-9]\+:,dnf-plugins-core/\0," ../dnf-plugins-core-python3-pylint.log
#cd ..
TESTS_EXIT=$(($DNF_TESTS2_EXIT + $DNF_TESTS3_EXIT + $PLG_TESTS2_EXIT + $PLG_TESTS3_EXIT))
TESTS_EXIT_STR="$DNF_TESTS2_EXIT and $DNF_TESTS3_EXIT and $PLG_TESTS2_EXIT and $PLG_TESTS3_EXIT"
if [ $3 -ne 1 ]; then
    TESTS_EXIT=$(($TESTS_EXIT + $DNF_LINT2_EXIT + $DNF_LINT3_EXIT + $PLG_LINT2_EXIT + $PLG_LINT3_EXIT))
    TESTS_EXIT_STR="$TESTS_EXIT_STR and $DNF_LINT2_EXIT and $DNF_LINT3_EXIT and $PLG_LINT2_EXIT and $PLG_LINT3_EXIT"
fi
if [ $TESTS_EXIT -eq 0 ]; then
	echo "...test succeeded."
else
	echo "...test failed with $TESTS_EXIT_STR."
fi

EXIT=$(($HAWKEY_EXIT + $LIBREPO_EXIT + $LIBCOMPS_EXIT + $DNF_EXIT + $PLUGINS_EXIT + $TESTS_EXIT))
if [ $EXIT -eq 0 ]; then
	echo "...test succeeded."
else
	echo "...test failed with $EXIT."
fi
exit $EXIT
