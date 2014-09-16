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
import os
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


class _Executable(metaclass=abc.ABCMeta):  # pylint: disable=R0903

    """A file that can be executed."""

    def __init__(self):
        """Initialize the executable."""
        super().__init__()

    @abc.abstractmethod
    def __call__(self, args, cwd):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :return: the standard output
        :rtype: bytes
        :raise NotImplementedError: if not implemented

        """
        raise NotImplementedError('not implemented')


class _CmakeStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "cmake" executable.

    :ivar dn2content: file content for each source directory name
    :type dn2content: dict[str, str]
    :ivar fn2content: file content for each made name
    :type fn2content: dict[str, str]

    """

    def __init__(self, dn2content):
        """Initialize the stub.

        :param dn2content: file content for each source directory name
        :type dn2content: dict[str, str]

        """
        super().__init__()
        self.dn2content = dn2content
        self.fn2content = {}

    def __call__(self, args, cwd):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
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

    def __init__(self, dn2rev):
        """Initialize the stub.

        :param dn2rev: Git revision for each source repository name and for
           name of each directory containing the made archives
        :type dn2rev: dict[str, str]

        """
        super().__init__()
        self.dn2rev = dn2rev

    def __call__(self, args, cwd):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
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

    def __init__(self, cmake):
        """Initialize the stub.

        :param cmake: the "cmake" executable
        :type cmake: test.test_unit._CmakeStub

        """
        super().__init__()
        self.cmake = cmake
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
    :type test: test.test_unit.DNFBuildTestCase
    :ivar archive: the DNF's "archive" executable
    :type archive: test.test_unit._ArchiveStub
    :ivar streams: the standard streams
    :type streams: test.test_unit._StandardStreamsStub

    """

    def __init__(self, test, archive, streams):
        """Initialize the stub.

        :param test: the current test
        :type test: test.test_unit.DNFBuildTestCase
        :param archive: the DNF's "archive" executable
        :type archive: test.test_unit._ArchiveStub
        :param streams: the standard streams
        :type streams: test.test_unit._StandardStreamsStub

        """
        super().__init__()
        self.test = test
        self.archive = archive
        self.streams = streams

    def __call__(self, args, cwd):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :return: the standard output
        :rtype: bytes

        """
        self.test.dn2tuple[os.path.join(cwd, args[3][12:])] = (
            self.streams.fn2file[os.path.join(cwd, args[6][7:])].getvalue(),
            self.archive.dn2rev[os.path.join(cwd, args[7][10:])],
            args[2][7:])
        return b''


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


class _SubprocessStub(object):

    """Testing stub of the "subprocess" module.

    :ivar fn2exe: executable for each file name
    :type fn2exe: dict[str, test.test_unit._Executable]
    :ivar path_fn2exe: executable for each file name available in the PATH
       environment variable
    :type path_fn2exe: dict[str, test.test_unit._Executable]

    """

    def __init__(self, fn2exe, path_fn2exe=None):
        """Initialize the stub.

        :param fn2exe: executable for each file name
        :type fn2exe: dict[str, test.test_unit._Executable]
        :param path_fn2exe: executable for each file name available in the PATH
           environment variable
        :type path_fn2exe: dict[str, test.test_unit._Executable] | None

        """
        super().__init__()
        self.fn2exe = fn2exe
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
        self.check_output(args, cwd)
        return 0

    def check_output(self, args, cwd):
        """Call an executable.

        :param args: the command line arguments
        :type args: list[str]
        :param cwd: name of the working directory
        :type cwd: str
        :return: the standard output
        :rtype: bytes

        """
        filename = args[0]
        exe = self.fn2exe.get(
            os.path.join(cwd, filename), self.path_fn2exe.get(filename))
        return exe(args, cwd)


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


class DNFBuildTestCase(unittest.TestCase):  # pylint: disable=R0904

    """DNF build environment test case.

    :ivar dn2tuple: spec file content, Git revision and Mock root for name of
       each directory containing the made SRPMs
    :type dn2tuple: dict[str, tuple[str, str, str]]

    """

    def setUp(self):
        """Prepare the test fixture."""
        super().setUp()
        self.dn2tuple = {}

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


if __name__ == '__main__':
    unittest.main()
