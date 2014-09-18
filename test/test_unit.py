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

"""Test isolated units of the source code."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import abc
import contextlib
import io
import itertools
import os
import subprocess
import tempfile
import unittest.mock

import dnf_ci


class _GitStub(object):  # pylint: disable=too-few-public-methods

    """Testing stub of the "git" executable.

    :ivar test: the current test
    :type test: test.test_unit.GitExecutableTestCase
    :ivar difffiles_repo2status: exit status of "git diff-files" command for
       each repository
    :type difffiles_repo2status: dict[str, int]
    :ivar diffindex_repo2statuses: exit statuses of "git diff-index" command
       for each index update and repository
    :type diffindex_repo2statuses: dict[str, list[int]]

    """

    def __init__(self, test, difffiles, diffindex):
        """Initialize the stub.

        :param test: the current test
        :type test: test.test_unit.GitExecutableTestCase
        :param difffiles_repo2status: exit status of "git diff-files" command
           for each repository
        :type difffiles_repo2status: dict[str, int]
        :param diffindex_repo2statuses: exit statuses of "git diff-index"
           command for each index update and repository
        :type diffindex_repo2statuses: dict[str, list[int]]

        """
        self.test = test
        self.difffiles_repo2status = difffiles
        self.diffindex_repo2statuses = diffindex

    def __call__(self, args):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :return: the exit status
        :rtype: int

        """
        if args[1] == 'clone':
            self.test.repo2source[args[4]] = args[3]
            return 0
        else:
            if args[3] == 'update-index':
                statuses = self.diffindex_repo2statuses[args[2]]
                if len(statuses) > 1:
                    statuses.pop(0)
            elif args[3] == 'diff-files':
                return self.difffiles_repo2status[args[2]]
            elif args[3] == 'diff-index':
                return self.diffindex_repo2statuses[args[2]][0]


class _MockResultsTestCase(unittest.TestCase):  # pylint: disable=R0904

    """Test case interested in "mock" executable results.

    :ivar root2packages: installed packages for each Mock root
    :type root2packages: dict[str, set[str]]
    :ivar dn2tuple: spec file content, Git revision and Mock root for name of
       each directory containing the made SRPMs
    :type dn2tuple: dict[str, tuple[str, str, str]]

    """

    def setUp(self):
        """Prepare the test fixture."""
        super().setUp()
        self.root2packages = {}
        self.dn2tuple = {}


class _Executable(metaclass=abc.ABCMeta):  # pylint: disable=R0903

    """A file that can be executed."""

    def __init__(self):
        """Initialize the executable."""
        super().__init__()

    @abc.abstractmethod
    def __call__(self, args, cwd, env, privileged):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param env: value for each environment variable
        :type env: dict[str, str]
        :param privileged: call with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes
        :raise NotImplementedError: if not implemented
        :raise subprocess.CalledProcessError: if the exit status is not zero

        """
        raise NotImplementedError('not implemented')


class _CmakeStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "cmake" executable.

    :ivar dn2content: file content for each source directory name
    :type dn2content: dict[str, str]
    :ivar fn2content: file content for each made name
    :type fn2content: dict[str, str]

    """

    def __init__(self, dn2content=None):
        """Initialize the stub.

        :param dn2content: file content for each source directory name
        :type dn2content: dict[str, str] | None

        """
        super().__init__()
        self.dn2content = dn2content or {}
        self.fn2content = {}

    def __call__(self, args, cwd, env, privileged):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param env: value for each environment variable
        :type env: dict[str, str]
        :param privileged: call with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes

        """
        content = self.dn2content[os.path.normpath(os.path.join(cwd, args[1]))]
        self.fn2content[os.path.join(cwd, 'package', 'dnf.spec')] = content
        return b''


class _ArchiveStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the DNF's "archive" executable.

    :ivar dn2rev: Git revision for each source repository name and for name of
       each directory containing the made archives
    :type dn2rev: dict[str, str]

    """

    def __init__(self, dn2rev=None):
        """Initialize the stub.

        :param dn2rev: Git revision for each source repository name and for
           name of each directory containing the made archives
        :type dn2rev: dict[str, str] | None

        """
        super().__init__()
        self.dn2rev = dn2rev or {}

    def __call__(self, args, cwd, env, privileged):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param env: value for each environment variable
        :type env: dict[str, str]
        :param privileged: call with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes

        """
        revision = self.dn2rev[cwd]
        self.dn2rev[os.path.expandvars('$HOME/rpmbuild/SOURCES')] = revision
        return (revision + '\n').encode()


class _StandardStreamsStub(object):

    """Testing stub of the standard streams.

    :ivar cmake: the "cmake" executable
    :type cmake: test.test_unit._CmakeStub
    :ivar stdout: the current testing standard output
    :type stdout: io.StringIO
    :ivar fn2file: file for each file name (both input and output)
    :type fn2file: dict[str, io.StringIO]

    """

    def __init__(self, cmake=None):
        """Initialize the stub.

        :param cmake: the "cmake" executable
        :type cmake: test.test_unit._CmakeStub | None

        """
        super().__init__()
        self.cmake = cmake or _CmakeStub()
        self.stdout = io.StringIO()
        self.fn2file = {}

    def print_(self, object_):
        """Print an object to the current testing standard output.

        :param object_: the object
        :type object_: object

        """
        print(object_, file=self.stdout)

    @contextlib.contextmanager  # pylint: disable=unused-argument
    def fileinput(self, files, inplace):
        """Create a loop over files.

        :param files: name of the file
        :type files: str
        :param inplace: ``True``
        :type inplace: bool
        :return: context manager returning the merged input
        :rtype: contextmanager[io.StringIO]

        """
        stdout_, self.stdout = self.stdout, io.StringIO()
        try:
            yield io.StringIO(self.cmake.fn2content[files])
        finally:
            self.fn2file[files], self.stdout = self.stdout, stdout_


class _MockStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "mock" executable.

    :ivar test: the current test
    :type test: test.test_unit._MockResultsTestCase
    :ivar archive: the DNF's "archive" executable
    :type archive: test.test_unit._ArchiveStub
    :ivar streams: the standard streams
    :type streams: test.test_unit._StandardStreamsStub
    :ivar dn2src: source for each directory name
    :type dn2src: dict[str, str]
    :ivar root2subprocess: "subprocess" module for each Mock root
    :type root2subprocess: dict[str, test.test_unit._SubprocessStub]

    """

    def __init__(self, test, archive=None, streams=None):
        """Initialize the stub.

        :param test: the current test
        :type test: test.test_unit._MockResultsTestCase
        :param archive: the DNF's "archive" executable
        :type archive: test.test_unit._ArchiveStub | None
        :param streams: the standard streams
        :type streams: test.test_unit._StandardStreamsStub | None

        """
        super().__init__()
        self.test = test
        self.archive = archive or _ArchiveStub()
        self.streams = streams or _StandardStreamsStub()
        self.dn2src = {}
        self.root2subprocess = {}

    @staticmethod
    def _rootpath(root, path):
        """Get host path for a path in a Mock root.

        :param root: name of the root
        :type root: str
        :param path: the path name
        :type path: str
        :return: the host path name
        :rtype: str

        """
        return os.path.join(
            tempfile.gettempdir(), 'mock', root, path.lstrip(os.sep))

    def _install(self, root, packages):
        """Install packages into a root.

        :param root: name of the root
        :type root: str
        :param packages: the packages as an argument for "yum install" command
        :type packages: list[str]

        """
        self.test.root2packages[root] = set(packages)

    def _copyin(self, root, source, destination):
        """Copy a directory recursively into a root.

        :param root: name of the root
        :type root: str
        :param source: name of the file or directory on the host
        :type source: str
        :param destination: name of the non-existant directory inside the root
        :type destination: str
        :return: the exit status
        :rtype: int

        """
        destination = self._rootpath(root, destination)
        if destination in self.dn2src:
            return 1
        self.dn2src[destination] = source
        return 0

    def _exec(self, root, cmdline, cwd, privileged):
        """Run a command non-interactively within a root.

        :param root: name of the root
        :type root: str
        :param cmdline: the command to be run
        :type cmdline: str
        :param cwd: name of a working directory relative to the root directory
        :type cwd: str
        :param privileged: run with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes
        :raise subprocess.CalledProcessError: if the exit status is not zero

        """
        return self.root2subprocess[root].check_output(
            cmdline.split(), self._rootpath(root, cwd), privileged)

    def _buildsrpm(  # pylint: disable=too-many-arguments
            self, root, spec, sources, result, cwd):
        """Build an SRPM within a root.

        :param root: name of the root
        :type root: str
        :param spec: name of the spec file on the host
        :type spec: str
        :param sources: name of the sources directory on the host
        :type sources: str
        :param result: name of the result directory on the host
        :type result: str
        :param cwd: name of a working directory
        :type cwd: str

        """
        self.test.dn2tuple[os.path.join(cwd, result)] = (
            self.streams.fn2file[os.path.join(cwd, spec)].getvalue(),
            self.archive.dn2rev[os.path.join(cwd, sources)],
            root)

    def __call__(self, args, cwd, env, privileged):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param env: value for each environment variable
        :type env: dict[str, str]
        :param privileged: call with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes
        :raise subprocess.CalledProcessError: if the exit status is not zero

        """
        status, output, root = 0, b'', args[2][7:]
        if args[3] == '--install':
            self._install(root, args[4:])
        elif args[3] == '--copyin':
            status = self._copyin(root, os.path.join(cwd, args[4]), args[5])
        elif '--chroot' in args[4:6]:
            normargs, priv = args[:], True
            if normargs[3] == '--unpriv':
                normargs.pop(3)
                priv = False
            try:
                output = self._exec(root, normargs[5], normargs[3][6:], priv)
            except subprocess.CalledProcessError as err:
                status, output = err.returncode, err.output
        else:
            self._buildsrpm(root, args[6][7:], args[7][10:], args[3][12:], cwd)
        if status:
            raise subprocess.CalledProcessError(status, args, output)
        return output


class _MockchainStub(object):  # pylint: disable=too-few-public-methods

    """Testing stub of the "mockchain" executable.

    :ivar test: the current test
    :type test: test.test_unit.MockchainTestCase
    :ivar failing: names of SRPMS that cannot be built
    :type failing: str[str]

    """

    def __init__(self, test, failing):
        """Initialize the stub.

        :param test: the current test
        :type test: test.test_unit.MockchainTestCase
        :param failing: names of SRPMS that cannot be built
        :type failing: set[str]

        """
        super().__init__()
        self.test = test
        self.failing = failing

    def __call__(self, args):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :return: the exit status
        :rtype: int

        """
        srpms = set(args[3:])
        if srpms & self.failing:
            return 1
        self.test.dn2tuple[args[2][12:]] = (srpms, args[1][7:])
        return 0


class _RmStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "rm" executable.

    :ivar mock: the "mock" executable
    :type mock: test.test_unit._MockStub

    """

    def __init__(self, mock):
        """Initialize the stub.

        :param mock: the "mock" executable
        :type mock: test.test_unit._MockStub

        """
        super().__init__()
        self.mock = mock

    def __call__(self, args, cwd, env, privileged):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param env: value for each environment variable
        :type env: dict[str, str]
        :param privileged: call with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes

        """
        dirname = os.path.normpath(os.path.join(cwd, args[3].lstrip(os.sep)))
        self.mock.dn2src.pop(dirname, None)
        return b''


class _ChownStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "chown" executable.

    :ivar dn2group: group name for each directory name
    :type dn2group: dict[str, str]

    """

    def __init__(self):
        """Initialize the stub."""
        super().__init__()
        self.dn2group = {}

    def __call__(self, args, cwd, env, privileged):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param env: value for each environment variable
        :type env: dict[str, str]
        :param privileged: call with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes

        """
        dirname = os.path.normpath(os.path.join(cwd, args[3].lstrip(os.sep)))
        self.dn2group[dirname] = args[2][1:]
        return b''


class _NoseStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "nosetests" executable.

    :ivar mock: the "mock" executable
    :type mock: test.test_unit._MockStub
    :ivar chown: the "chown" executable
    :type chown: test.test_unit._ChownStub
    :ivar tuple2exit: exit status of each process for each directory name,
       test, output capturing, LANG variable, LC_ALL variable, group name and
       privileges
    :type tuple2exit: dict[tuple[str, str, bool, str, str, str, bool], int]

    """

    def __init__(self, mock, chown, tuple2exit):
        """Initialize the stub.

        :param mock: the "mock" executable
        :type mock: test.test_unit._MockStub
        :param chown: the "chown" executable
        :type chown: test.test_unit._ChownStub
        :param tuple2exit: exit status of each process for each directory name,
           test, output capturing, LANG variable, LC_ALL variable, group name
           and privileges
        :type tuple2exit:
           dict[tuple[str, str, bool, str, str, str, bool], int]

        """
        super().__init__()
        self.mock = mock
        self.chown = chown
        self.tuple2exit = tuple2exit

    def __call__(self, args, cwd, env, privileged):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param env: value for each environment variable
        :type env: dict[str, str]
        :param privileged: call with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes
        :raise subprocess.CalledProcessError: if the exit status is not zero

        """
        normargs, capture = args[:], True
        if normargs[2] == '--nocapture':
            normargs.pop(2)
            capture = False
        status = self.tuple2exit[
            self.mock.dn2src[cwd], normargs[2], capture, env['LANG'],
            env['LC_ALL'], self.chown.dn2group[cwd], privileged]
        if status:
            raise subprocess.CalledProcessError(status, args, b'')
        return b''


class _SubprocessStub(object):

    """Testing stub of the "subprocess" module.

    :ivar fn2exe: executable for each file name
    :type fn2exe: dict[str, test.test_unit._Executable]
    :ivar path_fn2exe: executable for each file name available in the PATH
       environment variable
    :type path_fn2exe: dict[str, test.test_unit._Executable]

    """

    def __init__(self, fn2exe=None, path_fn2exe=None):
        """Initialize the stub.

        :param fn2exe: executable for each file name
        :type fn2exe: dict[str, test.test_unit._Executable] | None
        :param path_fn2exe: executable for each file name available in the PATH
           environment variable
        :type path_fn2exe: dict[str, test.test_unit._Executable] | None

        """
        super().__init__()
        self.fn2exe = fn2exe or {}
        self.path_fn2exe = path_fn2exe or {}

    def call(self, args, cwd='.'):
        """Call an executable.

        :param args: the command line arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :return: the exit status
        :rtype: int

        """
        try:
            self.check_output(args, cwd)
        except subprocess.CalledProcessError as err:
            return err.returncode
        return 0

    def check_output(self, args, cwd, privileged=False):
        """Call an executable.

        :param args: the command line arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :param privileged: call with root privileges
        :type privileged: bool
        :return: the standard output
        :rtype: bytes
        :raise subprocess.CalledProcessError: if the exit status is not zero

        """
        env = [arg.split('=', 1)
               for arg in itertools.takewhile(lambda arg: '=' in arg, args)]
        args = args[len(env):]
        filename = args[0]
        exe = self.fn2exe.get(
            os.path.join(cwd, filename), self.path_fn2exe.get(filename))
        return exe(args, cwd, dict(env), privileged)


class GitExecutableTestCase(unittest.TestCase):  # pylint: disable=R0904

    """Git executable test case.

    :ivar repo2source: source repository for each repository
    :type repo2source: dict[str, str]

    """

    def setUp(self):
        """Prepare the test fixture."""
        super().setUp()
        self.repo2source = {}

    @contextlib.contextmanager
    def patch(self, repository, difffiles=0, diffindex=None):
        """Return a context manager that patch all the relevant functions.

        :param repository: name of a repository used
        :type repository: str
        :param difffiles: exit status of "git diff-files" command
        :type difffiles: int
        :param diffindex: exit statuses of "git diff-index" command for each
           index update
        :type diffindex: list[int] | None
        :return: the context manager
        :rtype: contextmanager

        """
        git = _GitStub(
            self, {repository: difffiles}, {repository: diffindex or [0]})
        with unittest.mock.patch('subprocess.call', git):
            yield

    def test_uncommitted_changes(self):
        """Test check with all changes committed.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir()):
            found = dnf_ci.uncommitted_changes(tempfile.gettempdir())
        self.assertFalse(found, 'found')

    def test_uncommitted_changes_tree(self):
        """Test check with unstaged changes.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir(), difffiles=1):
            found = dnf_ci.uncommitted_changes(tempfile.gettempdir())
        self.assertTrue(found, 'not found')

    def test_uncommitted_changes_index(self):
        """Test check with staged changes.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir(), diffindex=[1]):
            found = dnf_ci.uncommitted_changes(tempfile.gettempdir())
        self.assertTrue(found, 'not found')

    def test_uncommitted_changes_refresh(self):  # pylint: disable=invalid-name
        """Test check with a false positive.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir(), diffindex=[1, 0]):
            found = dnf_ci.uncommitted_changes(tempfile.gettempdir())
        self.assertFalse(found, 'not refreshed')

    def test_clone(self):
        """Test cloning.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir()):
            dnf_ci.clone(
                os.path.join(tempfile.gettempdir(), 'src'),
                os.path.join(tempfile.gettempdir(), 'tgt'))
        self.assertEqual(
            self.repo2source[os.path.join(tempfile.gettempdir(), 'tgt')],
            os.path.join(tempfile.gettempdir(), 'src'),
            'not cloned')


class DNFBuildTestCase(_MockResultsTestCase):  # pylint: disable=R0904

    """DNF build environment test case."""

    @contextlib.contextmanager
    def patch(self, source, spec, revision):
        """Return a context manager that patch all the relevant functions.

        :param source: source Git repository used
        :type source: str
        :param spec: content of the source spec file
        :type spec: str
        :param revision: Git revision of the repository
        :type revision: str
        :return: the context manager
        :rtype: contextmanager

        """
        cmake = _CmakeStub({source: spec})
        archive = _ArchiveStub({source: revision})
        mock = _MockStub(self, archive, _StandardStreamsStub(cmake))
        subp = _SubprocessStub(
            {os.path.join(source, 'package', 'archive'): archive},
            {'cmake': mock.streams.cmake, 'mock': mock})
        with \
                unittest.mock.patch(
                    'subprocess.call', subp.call), \
                unittest.mock.patch(
                    'subprocess.check_output', subp.check_output), \
                unittest.mock.patch(
                    'fileinput.FileInput', mock.streams.fileinput), \
                unittest.mock.patch(
                    'dnf_ci.print', mock.streams.print_, create=True):
            yield

    def test_build_dnf(self):
        """Test building.

        :raise AssertionError: if the test fails

        """
        destination = os.path.join(tempfile.gettempdir(), 'build')
        spec = '%global gitrev abCD012\nrest of original\n'
        with self.patch(tempfile.gettempdir(), spec, 'bcDE123'):
            dnf_ci.build_dnf(tempfile.gettempdir(), destination, 'root')
        self.assertEqual(
            self.dn2tuple[destination],
            ('%global gitrev bcDE123\nrest of original\n', 'bcDE123', 'root'),
            'not built')


class MockchainTestCase(unittest.TestCase):  # pylint: disable=R0904

    """Mockchain executable test case.

    :ivar dn2tuple: names of RPMS and Mock root for name of each directory
       containing the made SRPMs
    :type dn2tuple: dict[str, tuple[set[str], str]]

    """

    def setUp(self):
        """Prepare the test fixture."""
        super().setUp()
        self.dn2tuple = {}

    @contextlib.contextmanager
    def patch(self, failing=None):
        """Return a context manager that patch all the relevant functions.

        :param failing: names of SRPMS that cannot be built
        :type failing: set[str]
        :return: the context manager
        :rtype: contextmanager

        """
        mockchain = _MockchainStub(self, failing or set())
        with unittest.mock.patch('subprocess.call', mockchain):
            yield

    def test_build_rpms_buildable(self):
        """Test building with a buildable SRPM.

        :raise AssertionError: if the test fails

        """
        with self.patch():
            dnf_ci.build_rpms(
                [os.path.join(tempfile.gettempdir(), 'a.src.rpm'),
                 os.path.join(tempfile.gettempdir(), 'b.src.rpm')],
                os.path.join(tempfile.gettempdir(), 'build'),
                'root')
        self.assertEqual(
            self.dn2tuple[os.path.join(tempfile.gettempdir(), 'build')],
            ({os.path.join(tempfile.gettempdir(), 'a.src.rpm'),
              os.path.join(tempfile.gettempdir(), 'b.src.rpm')},
             'root'),
            'not built')

    def test_build_rpms_nonbuildable(self):
        """Test building with a non-buildable SRPM.

        :raise AssertionError: if the test fails

        """
        srpm = os.path.join(tempfile.gettempdir(), 'a.src.rpm')
        with self.assertRaises(ValueError, msg='not raised'):
            with self.patch({srpm}):
                dnf_ci.build_rpms([srpm], 'build', 'root')


class MockTestCase(_MockResultsTestCase):  # pylint: disable=R0904

    """Mock executable test case."""

    @contextlib.contextmanager
    def patch(self, cwd, tests, root, status=0):
        """Return a context manager that patch all the relevant functions.

        :param cwd: name of a working directory used
        :type cwd: str
        :param tests: tests used
        :type tests: str
        :param root: name of a Mock root used
        :type root: str
        :param status: exit status of some Nose processes
        :type status: int
        :return: the context manager
        :rtype: contextmanager

        """
        mktuple = (
            lambda capture=True, locale='en_US.UTF-8':
            (cwd, tests, capture, locale, locale, 'mockbuild', False))
        tuples = [
            mktuple(), mktuple(locale='cs_CZ.utf8'), mktuple(capture=False)]
        chown = _ChownStub()
        mock = _MockStub(self)
        mock.root2subprocess[root] = _SubprocessStub(path_fn2exe={
            'rm': _RmStub(mock),
            'chown': chown,
            'nosetests-2.7': _NoseStub(mock, chown, {
                tuple_: 0 for tuple_ in tuples}),
            'nosetests-3.4': _NoseStub(mock, chown, {
                tuple_: status for tuple_ in tuples})})
        subp = _SubprocessStub(path_fn2exe={'mock': mock})
        with unittest.mock.patch('subprocess.call', subp.call):
            yield

    def test_run_tests_successful(self):
        """Test running with successful tests.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir(), 'tests', 'root', 0):
            success = dnf_ci.run_tests(
                'tests', tempfile.gettempdir(), ['pkg1', 'pkg2'], 'root')
        self.assertTrue(success, 'tests failed')
        self.assertEqual(
            self.root2packages['root'],
            {'pkg1', 'pkg2', 'python-nose', 'python3-nose'},
            'not installed')

    def test_run_tests_failing(self):
        """Test running with failing tests.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir(), 'tests', 'root', 1):
            success = dnf_ci.run_tests(
                'tests', tempfile.gettempdir(), ['pkg1', 'pkg2'], 'root')
        self.assertFalse(success, 'tests succeeded')
        self.assertEqual(
            self.root2packages['root'],
            {'pkg1', 'pkg2', 'python-nose', 'python3-nose'},
            'not installed')


if __name__ == '__main__':
    unittest.main()
