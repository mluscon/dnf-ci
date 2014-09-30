#!/usr/bin/env python3.3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014  Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line interface of the program.

The command-line interface usage is::

    usage: PROG [-h] [-v] [-r DIRNAME] [-8 FILENAME] [-f FILENAME]
                [-l FILENAME] [-a {x86_64,i386}]
                SOURCE

    Test a DNF Git repository.

    positional arguments:
      SOURCE                name of a readable DNF Git repository

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      -r DIRNAME, --rpms DIRNAME
                            name of a writable directory for the RPMs
      -8 FILENAME, --pep8 FILENAME
                            name of a writable file for the Pep8 output
      -f FILENAME, --pyflakes FILENAME
                            name of a writable file for the Pyflakes output
      -l FILENAME, --pylint FILENAME
                            name of a writable file for the Pylint output
      -a {x86_64,i386}, --arch {x86_64,i386}
                            name of the supported testing architecture to be
                            used

    It is assumed that the workflow to make a DNF's SRPM is to build DNF, run
    "package/archive", change the value of "gitrev" variable at the first line
    of "package/dnf.spec" to the output of "package/archive" and run Mock with
    the sources path set to "$HOME/rpmbuild/SOURCES". It is also assumed that
    it is enough to run Pylint on the "dnf" and "tests" subdirectories and to
    run Nose on the "tests" subdirectory. "cmake", "git" and "mock" executables
    must be available. Standard output and standard error must be writable.
    Mock roots must be writable and the existing roots may be modified. Program
    cannot be called by a superuser. If multiple architectures are given, the
    Pep8, Pyflakes and Pylint output files will contain just the output of the
    run for the last (in alphabetical order) architecture. If the source
    repository contains uncommitted changes or the tests fail, the exit status
    is 1. If the command line is not valid, the exit status is 2. Otherwise, a
    status of 0 is returned.

"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import subprocess
import sys
import tempfile

import dnf_ci.api


class _OutputConf(object):  # pylint: disable=too-few-public-methods

    """Program output configuration.

    :ivar rpmdn: name of a writable directory for RPMs
    :type rpmdn: str | None
    :ivar pep8fn: name of a writable file for a Pep8 output
    :type pep8fn: str | None
    :ivar pyflakesfn: name of a writable file for a Pyflakes output
    :type pyflakesfn: str | None
    :ivar pylintfn: name of a writable file for a Pylint output
    :type pylintfn: str | None

    """

    def __init__(self, rpmdn, pep8fn, pyflakesfn, pylintfn):
        """Initialize the configuration.

        :param rpmdn: name of a writable directory for RPMs
        :type rpmdn: str | None
        :param pep8fn: name of a writable file for a Pep8 output
        :type pep8fn: str | None
        :param pyflakesfn: name of a writable file for a Pyflakes output
        :type pyflakesfn: str | None
        :param pylintfn: name of a writable file for a Pylint output
        :type pylintfn: str | None

        """
        self.rpmdn = rpmdn
        self.pep8fn = pep8fn
        self.pyflakesfn = pyflakesfn
        self.pylintfn = pylintfn


def _test_on_arch(repository, arch, outconf):
    """Test a DNF Git repository on an architecture.

    It is assumed that the workflow is to build DNF, run "package/archive",
    change the value of "gitrev" variable at the first line of
    "package/dnf.spec" to the output of "package/archive" and run Mock with
    the sources path set to "$HOME/rpmbuild/SOURCES". It is also assumed that
    it is enough to run Pylint on the "dnf" and "tests" subdirectories and to
    run Nose on the "tests" subdirectory. "cmake", "git" and "mock" executables
    must be available. Standard output and standard error must be writable.
    Mock roots must be writable and the existing roots may be modified. This
    function cannot be called by a superuser. If the tests fail, the exit
    status is 1. Otherwise, a status of 0 is returned.

    :param repository: name of the readable DNF Git repository
    :type repository: str
    :param arch: the one of the following architectures to be used: x86_64 or
       i386
    :type arch: str
    :param outconf: program output configuration
    :type outconf: dnf_ci.cli._OutputConf
    :return: the exit status
    :rtype: int

    """
    with tempfile.TemporaryDirectory(prefix=dnf_ci.NAME + '-') as dirname:
        clonedn = os.path.join(dirname, 'repo-dnf')
        dnf_ci.api.clone(repository, clonedn)
        srpmdn = os.path.join(dirname, 'srpms')
        mockcfg = os.path.join(dirname, arch + '.cfg')
        with open(mockcfg, 'w', encoding='utf-8') as file:
            dnf_ci.api.write_mockcfg(file, arch)
        dnf_ci.api.build_dnf(clonedn, srpmdn, mockcfg)
        srpms = (
            os.path.join(root_dirs_files[0], basename)
            for root_dirs_files in os.walk(srpmdn)
            for basename in root_dirs_files[2]
            if basename.endswith('.src.rpm'))
        rpmdn = os.path.join(
            outconf.rpmdn or os.path.join(dirname, 'rpms'), arch)
        try:
            dnf_ci.api.build_rpm(next(srpms), rpmdn, mockcfg)
        except ValueError:
            print('RPM build failed.', file=sys.stderr)
        try:
            output = dnf_ci.api.pep8_isolated(clonedn, mockcfg)
        except subprocess.CalledProcessError as err:
            print('Pep8 failed. See the log file.', file=sys.stderr)
            output = err.output
        if outconf.pep8fn:
            with open(outconf.pep8fn, 'wb') as file:
                file.write(output)
        try:
            output = dnf_ci.api.pyflakes_isolated(clonedn, mockcfg)
        except subprocess.CalledProcessError as err:
            print('Pyflakes failed. See the log file.', file=sys.stderr)
            output = err.output
        if outconf.pyflakesfn:
            with open(outconf.pyflakesfn, 'wb') as file:
                file.write(output)
        rpms = [
            os.path.join(root_dirs_files[0], basename)
            for root_dirs_files in os.walk(rpmdn)
            for basename in root_dirs_files[2]
            if basename.endswith('.rpm')]
        try:
            output = dnf_ci.api.pylint_isolated(
                ['dnf', 'tests'], clonedn, rpms, mockcfg)
        except subprocess.CalledProcessError as err:
            print('Pylint failed. See the log file.', file=sys.stderr)
            output = err.output
        if outconf.pylintfn:
            with open(outconf.pylintfn, 'wb') as file:
                file.write(output)
        if not dnf_ci.api.run_tests('tests', clonedn, rpms, mockcfg):
            print('Tests failed.', file=sys.stderr)
            return 1
    return 0


def main():
    """Execute the command-line interface event loop.

    The command-line interface usage is::

        usage: PROG [-h] [-v] [-r DIRNAME] [-8 FILENAME] [-f FILENAME]
                    [-l FILENAME] [-a {x86_64,i386}]
                    SOURCE

        Test a DNF Git repository.

        positional arguments:
          SOURCE                name of a readable DNF Git repository

        optional arguments:
          -h, --help            show this help message and exit
          -v, --version         show program's version number and exit
          -r DIRNAME, --rpms DIRNAME
                                name of a writable directory for the RPMs
          -8 FILENAME, --pep8 FILENAME
                                name of a writable file for the Pep8 output
          -f FILENAME, --pyflakes FILENAME
                                name of a writable file for the Pyflakes output
          -l FILENAME, --pylint FILENAME
                                name of a writable file for the Pylint output
          -a {x86_64,i386}, --arch {x86_64,i386}
                                name of the supported testing architecture to
                                be used

        It is assumed that the workflow to make a DNF's SRPM is to build DNF,
        run "package/archive", change the value of "gitrev" variable at the
        first line of "package/dnf.spec" to the output of "package/archive" and
        run Mock with the sources path set to "$HOME/rpmbuild/SOURCES". It is
        also assumed that it is enough to run Pylint on the "dnf" and "tests"
        subdirectories and to run Nose on the "tests" subdirectory. "cmake",
        "git" and "mock" executables must be available. Standard output and
        standard error must be writable. Mock roots must be writable and the
        existing roots may be modified. Program cannot be called by a
        superuser. If multiple architectures are given, the Pep8, Pyflakes and
        Pylint output files will contain just the output of the run for the
        last (in alphabetical order) architecture. If the source repository
        contains uncommitted changes or the tests fail, the exit status is 1.
        If the command line is not valid, the exit status is 2. Otherwise, a
        status of 0 is returned.

    :raise SystemExit: with integer exit status at the end of the execution

    """
    parser = argparse.ArgumentParser(
        description='Test a DNF Git repository.',
        epilog="It is assumed that the workflow to make a DNF's SRPM is to "
        'build DNF, run "package/archive", change the value of "gitrev" '
        'variable at the first line of "package/dnf.spec" to the output of '
        '"package/archive" and run Mock with the sources path set to '
        '"$HOME/rpmbuild/SOURCES". It is also assumed that it is enough to '
        'run Pylint on the "dnf" and "tests" subdirectories and to run Nose on'
        ' the "tests" subdirectory. "cmake", "git" and "mock" executables must'
        ' be available. Standard output and standard error must be writable. '
        'Mock roots must be writable and the existing roots may be modified. '
        'Program cannot be called by a superuser. If multiple architectures '
        'are given, the Pep8, Pyflakes and Pylint output files will contain '
        'just the output of the run for the last (in alphabetical order) '
        'architecture. If the source repository contains uncommitted changes '
        'or the tests fail, the exit status is 1. If the command line is not '
        'valid, the exit status is 2. Otherwise, a status of 0 is returned.')
    parser.add_argument(
        '-v', '--version', action='version',
        version=dnf_ci.NAME + ' ' + dnf_ci.VERSION)
    parser.add_argument(
        '-r', '--rpms', help='name of a writable directory for the RPMs',
        metavar='DIRNAME')
    parser.add_argument(
        '-8', '--pep8', help='name of a writable file for the Pep8 output',
        metavar='FILENAME')
    parser.add_argument(
        '-f', '--pyflakes',
        help='name of a writable file for the Pyflakes output',
        metavar='FILENAME')
    parser.add_argument(
        '-l', '--pylint', help='name of a writable file for the Pylint output',
        metavar='FILENAME')
    parser.add_argument(
        '-a', '--arch', action='append', default=[],
        choices=['x86_64', 'i386'],
        help='name of the supported testing architecture to be used')
    parser.add_argument(
        'SOURCE', help='name of a readable DNF Git repository')
    arguments = parser.parse_args()

    if dnf_ci.api.uncommitted_changes(arguments.SOURCE):
        print('The repository contains uncommitted changes.', file=sys.stderr)
        sys.exit(1)
    outconf = _OutputConf(
        arguments.rpms, arguments.pep8, arguments.pyflakes, arguments.pylint)
    status = 0
    for arch in sorted(set(arguments.arch)):
        print('Current testing architecture: ' + arch)
        status = _test_on_arch(arguments.SOURCE, arch, outconf) or status
    sys.exit(status)


if __name__ == '__main__':
    main()
