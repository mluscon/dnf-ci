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

"""Test the units related to the command-line interface."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import io
import os
import subprocess
import tempfile
import time
import unittest.mock

import dnf_ci.cli


class CommandLineTestCase(unittest.TestCase):  # pylint: disable=R0904

    """Command line test case.

    :ivar stdstreams: standard output and standard error
    :type stdstreams: tuple[io.StringIO, io.StringIO]
    :ivar _clone_dn2repo: repository name for each cloned directory
    :type _clone_dn2repo: dict[str, str]
    :ivar _srpm2repo: repository name for each SRPM name
    :type _srpm2repo: dict[str, str]
    :ivar rpm2cfgrepo: Mock config and repository name for each RPM name
    :type rpm2cfgrepo: dict[str, tuple[str, str]]
    :ivar _output2phaserepo: phase name and repository name for each standard
       output
    :type _output2phaserepo: dict[bytes, tuple[str, str]]
    :ivar phase2fn2repo: repository name for each file name for each phase name
    :type phase2fn2repo: dict[str, dict[str, str]]
    :ivar _phase2repo2success: phase success for each repository name for each
       phase name
    :type _phase2repo2success: dict[str, dict[str, bool]]

    """

    def setUp(self):
        """Prepare the test fixture."""
        super().setUp()
        self.stdstreams = io.StringIO(), io.StringIO()
        self._clone_dn2repo = {}
        self._srpm2repo = {}
        self.rpm2cfgrepo = {}
        self._output2phaserepo = {}
        self.phase2fn2repo = {}
        self._phase2repo2success = {}

    @staticmethod
    def _iter_argv(  # pylint: disable=too-many-arguments
            repository, mockcfg, help_, version, rpms, pep8, pyflakes, pylint):
        """Return iterator over command line arguments.

        :param repository: name of a repository used
        :type repository: str
        :param mockcfg: name of a configuration file specifying a Mock root
        :type mockcfg: str
        :param help_: insert the help switch
        :type help_: bool
        :param version: insert the version switch
        :type version: bool
        :param rpms: name of a directory for the RPMs
        :type rpms: str | None
        :param pep8: name of a file for the Pep8 output
        :type pep8: str | None
        :param pyflakes: name of a file for the Pyflakes output
        :type pyflakes: str | None
        :param pylint: name of a file for the Pylint output
        :type pylint: str | None
        :return: the generator yielding the command line arguments
        :rtype: collections.abc.Iterator[str]

        """
        optional = lambda name, value: [name, value] if value else []
        yield 'prog'
        if help_:
            yield '-h'
        if version:
            yield '-v'
        yield from optional('-r', rpms)
        yield from optional('-8', pep8)
        yield from optional('-f', pyflakes)
        yield from optional('-l', pylint)
        yield repository
        yield mockcfg

    def _stub_clone(self, source, target):
        """Pretend to clone a Git repository.

        :param source: name of the source Git repository
        :type source: str
        :param target: name of the target directory
        :type target: str

        """
        self._clone_dn2repo[target] = source

    def _stub_build_dnf(  # pylint: disable=unused-argument
            self, source, destination, mockcfg):
        """Pretend to build a SRPM from a DNF Git repository.

        :param source: name of the source Git repository
        :type source: str
        :param destination: name of a directory for the results
        :type destination: str
        :param mockcfg: name of a configuration file specifying a Mock root
        :type mockcfg: str

        """
        srpm = os.path.join(
            destination, 'dnf-' + str(time.perf_counter()) + '.src.rpm')
        self._srpm2repo[srpm] = self._clone_dn2repo[source]

    def _stub_build_rpm(self, source, destination, mockcfg):
        """Pretend to build the RPMs from an SRPM.

        :param source: name of the SRPM file
        :type source: str
        :param destination: name of a directory for the results
        :type destination: str
        :param mockcfg: name of a configuration file specifying a Mock root
        :type mockcfg: str
        :raise ValueError: if the build fails

        """
        repo = self._srpm2repo[source]
        if not self._phase2repo2success['rpm'][repo]:
            raise ValueError('build failed')
        rpm = os.path.join(destination, str(time.perf_counter()) + '.rpm')
        self.rpm2cfgrepo[rpm] = (mockcfg, repo)

    def stub_walk(self, top):
        """Pretend to generate the file names in a directory tree.

        :param top: name of the tree
        :type top: str
        :return: the generator yielding a path to a directory, the list of its
           subdirectories' base names and the list of its files' base names
        :rtype: collections.abc.Iterator[tuple[str, list[str], list[str]]]

        """
        root2basenames = {}
        for filename in self._srpm2repo.keys() | self.rpm2cfgrepo.keys():
            if os.path.commonprefix([top, filename]) == top:
                root, basename = os.path.split(filename)
                root2basenames.setdefault(root, set()).add(basename)
        for root in sorted(root2basenames):
            yield (root, [], list(sorted(root2basenames[root])))

    def _stub_pep8_isolated(self, dirname, mockcfg):
        """Pretend to run "pep8" non-interactively in isolation.

        :param dirname: name of the directory to be checked
        :type dirname: str
        :param mockcfg: name of a configuration file specifying a Mock root
        :type mockcfg: str
        :return: standard output of the process
        :rtype: bytes
        :raise subprocess.CalledProcessError: if the exit status is not zero

        """
        output = str(time.perf_counter()).encode()
        repo = self._clone_dn2repo[dirname]
        self._output2phaserepo[output] = 'pep8', repo
        if not self._phase2repo2success['pep8'][repo]:
            raise subprocess.CalledProcessError(
                1, [mockcfg, 'pep8', dirname], output)
        return output

    def _stub_pyflakes_isolated(self, dirname, mockcfg):
        """Pretend to run "pyflakes" non-interactively in isolation.

        :param dirname: name of the directory to be checked
        :type dirname: str
        :param mockcfg: name of a configuration file specifying a Mock root
        :type mockcfg: str
        :return: standard output of the process
        :rtype: bytes
        :raise subprocess.CalledProcessError: if the exit status is not zero

        """
        output = str(time.perf_counter()).encode()
        repo = self._clone_dn2repo[dirname]
        self._output2phaserepo[output] = 'pyflakes', repo
        if not self._phase2repo2success['pyflakes'][repo]:
            raise subprocess.CalledProcessError(
                1, [mockcfg, 'pyflakes', dirname], output)
        return output

    def _stub_pylint_isolated(self, reldns, cwd, dependencies, mockcfg):
        """Pretend to run "pylint" non-interactively in isolation.

        :param reldns: names of directories to be checked relative to the
           working directory
        :type reldns: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param dependencies: required dependencies as an argument for
           "yum install" command
        :type dependencies: list[str]
        :param mockcfg: name of a configuration file specifying a Mock root
        :type mockcfg: str
        :return: standard output of the process
        :rtype: bytes
        :raise subprocess.CalledProcessError: if the exit status is not zero

        """
        out, repo = str(time.perf_counter()).encode(), self._clone_dn2repo[cwd]
        crs = (self.rpm2cfgrepo.get(rpm, (None, None)) for rpm in dependencies)
        deprepos = (repo_ for cfg, repo_ in crs if cfg == mockcfg)
        exccmd = [mockcfg] + dependencies + ['pylint', cwd] + reldns
        if repo not in deprepos:
            out = (
                cwd.encode() +
                b":1: [F0401(import-error), foo] Unable to import 'bar'")
            raise subprocess.CalledProcessError(1, exccmd, out)
        self._output2phaserepo[out] = 'pylint', repo
        if not self._phase2repo2success['pylint'][repo]:
            raise subprocess.CalledProcessError(1, exccmd, out)
        return out

    @contextlib.contextmanager  # pylint: disable=unused-argument
    def _stub_open(self, file, mode):
        """Pretend to open a file.

        :param file: name of the file
        :type file: str
        :param mode: the mode in which the file is opened
        :type mode: str
        :return: context manager returning the file
        :rtype: contextmanager[io.BufferedWriter]

        """
        def write(bytes_):
            """Pretend to write bytes to a file.

            :param bytes_: the bytes
            :type bytes_: bytes

            """
            phase, repository = self._output2phaserepo[bytes_]
            self.phase2fn2repo[phase] = {file: repository}
        file_ = unittest.mock.create_autospec(io.BufferedWriter)
        file_.write.side_effect = write
        yield file_

    def _stub_run_tests(  # pylint: disable=unused-argument
            self, tests, cwd, dependencies, mockcfg):
        """Pretend to run unit tests.

        :param tests: the tests to be run
        :type tests: str
        :param cwd: name of the working directory
        :type cwd: str
        :param dependencies: required dependencies as an argument for
           "yum install" command
        :type dependencies: list[str]
        :param mockcfg: name of a configuration file specifying a Mock root
        :type mockcfg: str
        :return: tests succeeded
        :rtype: bool

        """
        repo = self._clone_dn2repo[cwd]
        crs = (self.rpm2cfgrepo.get(rpm, (None, None)) for rpm in dependencies)
        deprepos = (repo_ for cfg, repo_ in crs if cfg == mockcfg)
        if repo not in deprepos:
            return False
        return self._phase2repo2success['tests'][repo]

    @contextlib.contextmanager
    def patch(  # pylint: disable=too-many-arguments
            self, repository, mockcfg, help_=False, version=False,
            uncommitted=False, rpms=None, pep8=None, pyflakes=None,
            pylint=None, success=True):
        """Return a context manager that patch all the relevant functions.

        :param repository: name of a repository used
        :type repository: str | None
        :param mockcfg: name of a configuration file specifying a Mock root
           used
        :type mockcfg: str
        :param help_: insert the help switch into the command line arguments
        :type help_: bool
        :param version: insert the version switch into the command line
           arguments
        :type version: bool
        :param uncommitted: the repository contains uncommitted changes
        :type uncommitted: bool
        :param rpmsuccess: RPM build succeeds
        :type rpmsuccess: bool
        :param rpms: name of a directory for the RPMs
        :type rpms: str | bool | None
        :param pep8: name of a file for the Pep8 output
        :type pep8: str | bool | None
        :param pyflakes: name of a file for the Pyflakes output
        :type pyflakes: str | bool | None
        :param pylint: name of a file for the Pylint output
        :type pylint: str | bool | None
        :param success: tests succeed
        :type success: bool
        :return: the context manager
        :rtype: contextmanager

        """
        argv = ['prog'] if repository is None else list(self._iter_argv(
            repository, mockcfg, help_, version, rpms, pep8, pyflakes, pylint))
        phase2success = {
            'rpm': rpms is not False,
            'pep8': pep8 is not False,
            'pyflakes': pyflakes is not False,
            'pylint': pylint is not False,
            'tests': success}
        self._phase2repo2success = {
            phase: {repository: succ} for phase, succ in phase2success.items()}
        with \
                unittest.mock.patch(
                    'sys.argv', argv), \
                unittest.mock.patch(
                    'sys.stdout', self.stdstreams[0]), \
                unittest.mock.patch(
                    'sys.stderr', self.stdstreams[1]), \
                unittest.mock.patch(
                    'dnf_ci.api.uncommitted_changes',
                    {repository: uncommitted}.__getitem__), \
                unittest.mock.patch(
                    'tempfile.TemporaryDirectory', autospec=True) as tempdir, \
                unittest.mock.patch(
                    'dnf_ci.api.clone', self._stub_clone), \
                unittest.mock.patch(
                    'dnf_ci.api.build_dnf', self._stub_build_dnf), \
                unittest.mock.patch(
                    'dnf_ci.api.build_rpm', self._stub_build_rpm), \
                unittest.mock.patch(
                    'os.walk', self.stub_walk, create=True), \
                unittest.mock.patch(
                    'dnf_ci.api.pep8_isolated', self._stub_pep8_isolated), \
                unittest.mock.patch(
                    'dnf_ci.api.pyflakes_isolated',
                    self._stub_pyflakes_isolated), \
                unittest.mock.patch(
                    'dnf_ci.api.pylint_isolated',
                    self._stub_pylint_isolated), \
                unittest.mock.patch(
                    'dnf_ci.cli.open', self._stub_open, create=True), \
                unittest.mock.patch(
                    'dnf_ci.api.run_tests', self._stub_run_tests):
            tempdir.return_value.__enter__.return_value = tempfile.gettempdir()
            yield

    def test_main_help(self):
        """Test execution with the help switch.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, help_=True):
                dnf_ci.cli.main()
        self.assertIn(
            'usage: prog [-h] [-v] [-r DIRNAME] [-8 FILENAME] [-f FILENAME] '
            '[-l FILENAME]\n            SOURCE MOCKCFG\n\nTest a DNF Git '
            'repository.\n\npositional arguments:\n  SOURCE                '
            'name of a readable DNF Git repository\n  MOCKCFG               '
            'name of a configuration file specifying a writable\n             '
            '           Mock root\n\noptional arguments:\n  -h, --help        '
            '    show this help message and exit\n  -v, --version         show'
            ' program\'s version number and exit\n  -r DIRNAME, --rpms DIRNAME'
            '\n                        name of a writable directory for the '
            'RPMs\n  -8 FILENAME, --pep8 FILENAME\n                        '
            'name of a writable file for the Pep8 output\n  -f FILENAME, '
            '--pyflakes FILENAME\n                        name of a writable '
            'file for the Pyflakes output\n  -l FILENAME, --pylint FILENAME\n '
            '                       name of a writable file for the Pylint '
            'output\n\nIt is assumed that the workflow to make a DNF\'s SRPM '
            'is to build DNF, run\n"package/archive", change the value of '
            '"gitrev" variable at the first line of\n"package/dnf.spec" to the'
            ' output of "package/archive" and run Mock with the\nsources path '
            'set to "$HOME/rpmbuild/SOURCES". It is also assumed that it is\n'
            'enough to run Pylint on the "dnf" and "tests" subdirectories and '
            'to run Nose\non the "tests" subdirectory. "cmake", "git" and '
            '"mock" executables must be\navailable. Standard output and '
            'standard error must be writable. The Mock root\nmay be modified. '
            'Program cannot be called by a superuser. If the source\n'
            'repository contains uncommitted changes or the tests fail, the '
            'exit status is\n1. If the command line is not valid, the exit '
            'status is 2. Otherwise, a status\nof 0 is returned.\n',
            self.stdstreams[0].getvalue(),
            'not printed')
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')

    def test_main_version(self):
        """Test execution with the version switch.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, version=True):
                dnf_ci.cli.main()
        self.assertIn(
            dnf_ci.VERSION, self.stdstreams[1].getvalue(), 'not printed')
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')

    def test_main_uncommitted(self):
        """Test execution with uncommitted changes.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, uncommitted=True):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 1, 'incorrect exit status')

    def test_main_rpm_failure(self):
        """Test execution with a failing RPM build.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, rpms=False):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 1, 'incorrect exit status')

    def test_main_rpms(self):
        """Test execution with an RPM directory.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        rpms = os.path.join(tempfile.gettempdir(), 'rpms')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, rpms=rpms):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')
        cfgrepos = {
            self.rpm2cfgrepo[os.path.join(root_dirs_files[0], basename)]
            for root_dirs_files in self.stub_walk(rpms)
            for basename in root_dirs_files[2]}
        self.assertEqual(
            cfgrepos, {(mockcfg, tempfile.gettempdir())},
            'incorrect repositories')

    def test_main_pep8_failure(self):
        """Test execution with a failing Pep8.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, pep8=False):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')

    def test_main_pep8(self):
        """Test execution with a Pep8 file.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        pep8 = os.path.join(tempfile.gettempdir(), 'pep8.log')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, pep8=pep8):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')
        self.assertEqual(
            self.phase2fn2repo['pep8'][pep8], tempfile.gettempdir(),
            'incorrect repository')

    def test_main_pyflakes_failure(self):
        """Test execution with a failing Pyflakes.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, pyflakes=False):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')

    def test_main_pyflakes(self):
        """Test execution with a Pyflakes file.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        pyflakes = os.path.join(tempfile.gettempdir(), 'pyflakes.log')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, pyflakes=pyflakes):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')
        self.assertEqual(
            self.phase2fn2repo['pyflakes'][pyflakes], tempfile.gettempdir(),
            'incorrect repository')

    def test_main_pylint_failure(self):
        """Test execution with a failing Pylint.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, pylint=False):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')

    def test_main_pylint(self):
        """Test execution with a Pylint file.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        pylint = os.path.join(tempfile.gettempdir(), 'pylint.log')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, pylint=pylint):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 0, 'incorrect exit status')
        self.assertEqual(
            self.phase2fn2repo['pylint'][pylint], tempfile.gettempdir(),
            'incorrect repository')

    def test_main_tests_failure(self):
        """Test execution with failing tests.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(tempfile.gettempdir(), mockcfg, success=False):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 1, 'incorrect exit status')

    def test_invalid(self):
        """Test execution with invalid command line arguments.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(SystemExit, msg='not raised') as context:
            with self.patch(None, mockcfg):
                dnf_ci.cli.main()
        self.assertEqual(context.exception.code, 2, 'incorrect exit status')


if __name__ == '__main__':
    unittest.main()
