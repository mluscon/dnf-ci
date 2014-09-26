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

"""Test the units related to the application programming interface."""


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

import dnf_ci.api


class _GitStub(object):  # pylint: disable=too-few-public-methods

    """Testing stub of the "git" executable.

    :ivar test: the current test
    :type test: test.unit.test_api.GitExecutableTestCase
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
        :type test: test.unit.test_api.GitExecutableTestCase
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

    :ivar cfg2packages: installed packages for each Mock config
    :type cfg2packages: dict[str, set[str]]
    :ivar dn2tuple: spec file content, Git revision and Mock config for name of
       each directory containing the made SRPMs
    :type dn2tuple: dict[str, tuple[str, str, str]]
    :ivar dn2srpmcfg: SRPM and Mock config for each directory containing the
       made RPMs
    :type dn2srpmcfg: dict[str, tuple[set[str], str]]

    """

    def setUp(self):
        """Prepare the test fixture."""
        super().setUp()
        self.cfg2packages = {}
        self.dn2tuple = {}
        self.dn2srpmcfg = {}


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
    :type cmake: test.unit.test_api._CmakeStub
    :ivar stdout: the current testing standard output
    :type stdout: io.StringIO
    :ivar fn2file: file for each file name (both input and output)
    :type fn2file: dict[str, io.StringIO]

    """

    def __init__(self, cmake=None):
        """Initialize the stub.

        :param cmake: the "cmake" executable
        :type cmake: test.unit.test_api._CmakeStub | None

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
    :type test: test.unit.test_api._MockResultsTestCase
    :ivar archive: the DNF's "archive" executable
    :type archive: test.unit.test_api._ArchiveStub
    :ivar streams: the standard streams
    :type streams: test.unit.test_api._StandardStreamsStub
    :ivar dn2src: source for each directory name
    :type dn2src: dict[str, str]
    :ivar cfg2subprocess: "subprocess" module for each Mock config
    :type cfg2subprocess: dict[str, test.unit.test_api._SubprocessStub]
    :ivar failing: name of the SRPM that cannot be built
    :type failing: str | None

    """

    def __init__(self, test, archive=None, streams=None, failing=None):
        """Initialize the stub.

        :param test: the current test
        :type test: test.unit.test_api._MockResultsTestCase
        :param archive: the DNF's "archive" executable
        :type archive: test.unit.test_api._ArchiveStub | None
        :param streams: the standard streams
        :type streams: test.unit.test_api._StandardStreamsStub | None
        :param failing: name of the SRPM that cannot be built
        :type failing: str | None

        """
        super().__init__()
        self.test = test
        self.archive = archive or _ArchiveStub()
        self.streams = streams or _StandardStreamsStub()
        self.dn2src = {}
        self.cfg2subprocess = {}
        self.failing = failing

    @staticmethod
    def _rootpath(config, path):
        """Get host path for a path in a Mock root.

        :param config: name of the config file
        :type config: str
        :param path: the path name
        :type path: str
        :return: the host path name
        :rtype: str

        """
        return os.path.join(config, path.lstrip(os.sep))

    @staticmethod
    def _split_commandline(line):
        """Split command line arguments.

        :param line: the command line
        :type line: str
        :return: generator yielding the command line arguments
        :rtype: collections.abc.Iterator[str]

        """
        start, nobreak = 0, False
        for end, character in enumerate(line):
            if character == '"':
                nobreak = not nobreak
            elif character == ' ' and not nobreak:
                yield line[start:end]
                start = end + 1
        yield line[start:]

    def _install(self, config, packages):
        """Install packages into a root.

        :param config: name of the config file
        :type config: str
        :param packages: the packages as an argument for "yum install" command
        :type packages: list[str]

        """
        self.test.cfg2packages[config] = set(packages)

    def _copyin(self, config, source, destination):
        """Copy a directory recursively into a root.

        :param config: name of the config file
        :type config: str
        :param source: name of the file or directory on the host
        :type source: str
        :param destination: name of the non-existant directory inside the root
        :type destination: str
        :return: the exit status
        :rtype: int

        """
        destination = self._rootpath(config, destination)
        if destination in self.dn2src:
            return 1
        self.dn2src[destination] = source
        return 0

    @staticmethod
    def _parse_exec_args(args):
        """Parse command line arguments for a command execution within a root.

        :param args: the command line arguments
        :type args: list[str]
        :return: the command, name of the working directory and the root
           privileges
        :rtype: tuple[str, str, bool]

        """
        args, privileged = args[:], True
        if args[4] == '--unpriv':
            args.pop(4)
            privileged = False
        return args[6], args[4][6:], privileged

    def _exec(self, config, cmdline, cwd, privileged):
        """Run a command non-interactively within a root.

        :param config: name of the config file
        :type config: str
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
        command = list(self._split_commandline(cmdline))
        return self.cfg2subprocess[config].check_output(
            command, self._rootpath(config, cwd), privileged)

    def _buildsrpm(  # pylint: disable=too-many-arguments
            self, config, spec, sources, result, cwd):
        """Build an SRPM within a root.

        :param config: name of the config file
        :type config: str
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
            config)

    def _rebuild(self, config, srpm, result, cwd):
        """Build an RPM within a root.

        :param config: name of the config file
        :type config: str
        :param srpm: name of the SRPM on the host
        :type srpm: str
        :param result: name of the result direcotyr on the host
        :type result: str
        :param cwd: name of a working directory
        :type cwd: str
        :return: the exit status
        :rtype: int

        """
        if srpm == self.failing:
            return 1
        self.test.dn2srpmcfg[os.path.join(cwd, result)] = (
            os.path.join(cwd, srpm), config)
        return 0

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
        status, output = 0, b''
        cfg = os.path.join(args[2][12:], args[3][7:] + '.cfg')
        if args[4] == '--install':
            self._install(cfg, args[5:])
        elif args[4] == '--copyin':
            status = self._copyin(cfg, os.path.join(cwd, args[5]), args[6])
        elif '--chroot' in args[5:7]:
            cmdline, rcwd, privileged = self._parse_exec_args(args)
            try:
                output = self._exec(cfg, cmdline, rcwd, privileged)
            except subprocess.CalledProcessError as err:
                status, output = err.returncode, err.output
        elif args[6] == '--buildsrpm':
            self._buildsrpm(cfg, args[7][7:], args[8][10:], args[4][12:], cwd)
        else:
            status = self._rebuild(cfg, args[7], args[4][12:], cwd)
        if status:
            raise subprocess.CalledProcessError(status, args, output)
        return output


class _MockchainStub(object):  # pylint: disable=too-few-public-methods

    """Testing stub of the "mockchain" executable.

    :ivar test: the current test
    :type test: test.unit.test_api.MockchainTestCase
    :ivar failing: names of SRPMS that cannot be built
    :type failing: str[str]

    """

    def __init__(self, test, failing):
        """Initialize the stub.

        :param test: the current test
        :type test: test.unit.test_api.MockchainTestCase
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
    :type mock: test.unit.test_api._MockStub

    """

    def __init__(self, mock):
        """Initialize the stub.

        :param mock: the "mock" executable
        :type mock: test.unit.test_api._MockStub

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
    :type mock: test.unit.test_api._MockStub
    :ivar chown: the "chown" executable
    :type chown: test.unit.test_api._ChownStub
    :ivar tuple2exit: exit status of each process for each directory name,
       test, output capturing, LANG variable, LC_ALL variable, group name and
       privileges
    :type tuple2exit: dict[tuple[str, str, bool, str, str, str, bool], int]

    """

    def __init__(self, mock, chown, tuple2exit):
        """Initialize the stub.

        :param mock: the "mock" executable
        :type mock: test.unit.test_api._MockStub
        :param chown: the "chown" executable
        :type chown: test.unit.test_api._ChownStub
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


class _Pep8Stub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "pep8" executable.

    :ivar mock: the "mock" executable
    :type mock: test.unit.test_api._MockStub
    :ivar dn2exitout: exit status and standard output of each process for each
       directory name
    :type dn2exitout: dict[str, tuple[int, bytes]]

    """

    def __init__(self, mock, dn2exitout):
        """Initialize the stub.

        :param mock: the "mock" executable
        :type mock: test.unit.test_api._MockStub
        :param dn2exitout: exit status and standard output of each process for
           each directory name
        :type dn2exitout: dict[str, tuple[int, bytes]]

        """
        super().__init__()
        self.mock = mock
        self.dn2exitout = dn2exitout

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
        status, output = self.dn2exitout[
            self.mock.dn2src[os.path.normpath(os.path.join(cwd, args[1]))]]
        if status:
            raise subprocess.CalledProcessError(status, args, output)
        return output


class _PyflakesStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "pyflakes" executable.

    :ivar mock: the "mock" executable
    :type mock: test.unit.test_api._MockStub
    :ivar dn2exitout: exit status and standard output of each process for each
       directory name
    :type dn2exitout: dict[str, tuple[int, bytes]]

    """

    def __init__(self, mock, dn2exitout):
        """Initialize the stub.

        :param mock: the "mock" executable
        :type mock: test.unit.test_api._MockStub
        :param dn2exitout: exit status and standard output of each process for
           each directory name
        :type dn2exitout: dict[str, tuple[int, bytes]]

        """
        super().__init__()
        self.mock = mock
        self.dn2exitout = dn2exitout

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
        status, output = self.dn2exitout[
            self.mock.dn2src[os.path.normpath(os.path.join(cwd, args[1]))]]
        if status:
            raise subprocess.CalledProcessError(status, args, output)
        return output


class _PylintStub(_Executable):  # pylint: disable=too-few-public-methods

    """Testing stub of the "pylint" executable.

    :ivar mock: the "mock" executable
    :type mock: test.unit.test_api._MockStub
    :ivar tuple2exitout: exit status and standard output of each process for
       each directory name and subdirectories' names
    :type tuple2exitout: dict[tuple[str, tuple[str]], tuple[int, bytes]]

    """

    def __init__(self, mock, tuple2exitout):
        """Initialize the stub.

        :ivar mock: the "mock" executable
        :type mock: test.unit.test_api._MockStub
        :ivar tuple2exitout: exit status and standard output of each process
           for each directory name and subdirectories' names
        :type tuple2exitout: dict[tuple[str, tuple[str]], tuple[int, bytes]]

        """
        super().__init__()
        self.mock = mock
        self.tuple2exitout = tuple2exitout

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
        status, output = self.tuple2exitout[
            self.mock.dn2src[cwd], tuple(args[3:])]
        if status:
            raise subprocess.CalledProcessError(status, args, output)
        return output


class _SubprocessStub(object):

    """Testing stub of the "subprocess" module.

    :ivar fn2exe: executable for each file name
    :type fn2exe: dict[str, test.unit.test_api._Executable]
    :ivar path_fn2exe: executable for each file name available in the PATH
       environment variable
    :type path_fn2exe: dict[str, test.unit.test_api._Executable]

    """

    def __init__(self, fn2exe=None, path_fn2exe=None):
        """Initialize the stub.

        :param fn2exe: executable for each file name
        :type fn2exe: dict[str, test.unit.test_api._Executable] | None
        :param path_fn2exe: executable for each file name available in the PATH
           environment variable
        :type path_fn2exe: dict[str, test.unit.test_api._Executable] | None

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

    def check_output(self, args, cwd='.', privileged=False):
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
            found = dnf_ci.api.uncommitted_changes(tempfile.gettempdir())
        self.assertFalse(found, 'found')

    def test_uncommitted_changes_tree(self):
        """Test check with unstaged changes.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir(), difffiles=1):
            found = dnf_ci.api.uncommitted_changes(tempfile.gettempdir())
        self.assertTrue(found, 'not found')

    def test_uncommitted_changes_index(self):
        """Test check with staged changes.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir(), diffindex=[1]):
            found = dnf_ci.api.uncommitted_changes(tempfile.gettempdir())
        self.assertTrue(found, 'not found')

    def test_uncommitted_changes_refresh(self):  # pylint: disable=invalid-name
        """Test check with a false positive.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir(), diffindex=[1, 0]):
            found = dnf_ci.api.uncommitted_changes(tempfile.gettempdir())
        self.assertFalse(found, 'not refreshed')

    def test_clone(self):
        """Test cloning.

        :raise AssertionError: if the test fails

        """
        with self.patch(tempfile.gettempdir()):
            dnf_ci.api.clone(
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
                    'dnf_ci.api.print', mock.streams.print_, create=True):
            yield

    def test_build_dnf(self):
        """Test building.

        :raise AssertionError: if the test fails

        """
        destination = os.path.join(tempfile.gettempdir(), 'build')
        spec = '%global gitrev abCD012\nrest of original\n'
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.patch(tempfile.gettempdir(), spec, 'bcDE123'):
            dnf_ci.api.build_dnf(tempfile.gettempdir(), destination, mockcfg)
        self.assertEqual(
            self.dn2tuple[destination],
            ('%global gitrev bcDE123\nrest of original\n', 'bcDE123', mockcfg),
            'not built')


class MockchainTestCase(unittest.TestCase):  # pylint: disable=R0904

    """Mockchain executable test case.

    :ivar dn2tuple: names of RPMS and Mock config for name of each directory
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
            dnf_ci.api.build_rpms(
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
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(ValueError, msg='not raised'):
            with self.patch({srpm}):
                dnf_ci.api.build_rpms([srpm], 'build', mockcfg)


class MockTestCase(_MockResultsTestCase):  # pylint: disable=R0904

    """Mock executable test case."""

    @contextlib.contextmanager
    def patch(  # pylint: disable=too-many-arguments
            self, cwd, mockcfg, failing=None, tests='tests', nose_exit=0,
            pep_exitout=(0, b''), flakes_exitout=(0, b''), lint_reldns=None,
            lint_exitout=(0, b'')):
        """Return a context manager that patch all the relevant functions.

        :param cwd: name of a working directory used
        :type cwd: str
        :param mockcfg: name of a configuration file specifying a Mock root
           used
        :type mockcfg: str
        :param failing: name of the SRPM that cannot be built
        :type failing: str | None
        :param tests: tests used
        :type tests: str
        :param nose_exit: exit status of some Nose processes
        :type nose_exit: int
        :param pep_exitout: exit status and standard output of all Pep8
           processes
        :type pep_exitout: tuple[int, bytes]
        :param lint_reldns: names of directories used with Pylint
        :type lint_reldns: list[str] | None
        :param lint_exitout: exit status and standard output of all Pylint
           processes
        :type lint_exitout: tuple[int, bytes]
        :return: the context manager
        :rtype: contextmanager

        """
        mktuple = (
            lambda capture=True, locale='en_US.UTF-8':
            (cwd, tests, capture, locale, locale, 'mockbuild', False))
        tuples = [
            mktuple(), mktuple(locale='cs_CZ.utf8'), mktuple(capture=False)]
        lint_reldns = tuple(lint_reldns or ())
        chown = _ChownStub()
        mock = _MockStub(self, failing=failing)
        mock.cfg2subprocess[mockcfg] = _SubprocessStub(path_fn2exe={
            'rm': _RmStub(mock),
            'chown': chown,
            'nosetests-2.7': _NoseStub(mock, chown, {
                tuple_: 0 for tuple_ in tuples}),
            'nosetests-3.4': _NoseStub(mock, chown, {
                tuple_: nose_exit for tuple_ in tuples}),
            'pep8': _Pep8Stub(mock, {
                cwd: pep_exitout}),
            'python3-pep8': _Pep8Stub(mock, {
                cwd: pep_exitout}),
            'pyflakes': _PyflakesStub(mock, {
                cwd: flakes_exitout}),
            'python3-pyflakes': _PyflakesStub(mock, {
                cwd: flakes_exitout}),
            'pylint': _PylintStub(mock, {
                (cwd, lint_reldns): lint_exitout}),
            'python3-pylint': _PylintStub(mock, {
                (cwd, lint_reldns): lint_exitout})})
        subp = _SubprocessStub(path_fn2exe={'mock': mock})
        with \
                unittest.mock.patch(
                    'subprocess.call', subp.call), \
                unittest.mock.patch(
                    'subprocess.check_output', subp.check_output):
            yield

    def test_build_rpm_buildable(self):
        """Test building with a buildable RPM.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.patch(tempfile.gettempdir(), mockcfg):
            dnf_ci.api.build_rpm(
                os.path.join(tempfile.gettempdir(), 'p.src.rpm'),
                os.path.join(tempfile.gettempdir(), 'build'),
                mockcfg)
        self.assertEqual(
            self.dn2srpmcfg[os.path.join(tempfile.gettempdir(), 'build')],
            (os.path.join(tempfile.gettempdir(), 'p.src.rpm'), mockcfg),
            'not built')

    def test_build_rpm_nonbuildable(self):
        """Test building with a non-buildable RPM.

        :raise AssertionError: if the test fails

        """
        srpm = os.path.join(tempfile.gettempdir(), 'p.src.rpm')
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.assertRaises(ValueError):
            with self.patch(tempfile.gettempdir(), mockcfg, failing=srpm):
                dnf_ci.api.build_rpm(
                    srpm, os.path.join(tempfile.gettempdir(), 'bld'), mockcfg)

    def test_run_tests_successful(self):
        """Test running with successful tests.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.patch(tempfile.gettempdir(), mockcfg, 'tests', nose_exit=0):
            success = dnf_ci.api.run_tests(
                'tests', tempfile.gettempdir(), ['pkg1', 'pkg2'], mockcfg)
        self.assertTrue(success, 'tests failed')
        self.assertEqual(
            self.cfg2packages[mockcfg],
            {'pkg1', 'pkg2', 'python-nose', 'python3-nose'},
            'not installed')

    def test_run_tests_failing(self):
        """Test running with failing tests.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.patch(tempfile.gettempdir(), mockcfg, 'tests', nose_exit=1):
            success = dnf_ci.api.run_tests(
                'tests', tempfile.gettempdir(), ['pkg1', 'pkg2'], mockcfg)
        self.assertFalse(success, 'tests succeeded')
        self.assertEqual(
            self.cfg2packages[mockcfg],
            {'pkg1', 'pkg2', 'python-nose', 'python3-nose'},
            'not installed')

    def test_pep8_isolated_successful(self):
        """Test running with successful checks.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.patch(tempfile.gettempdir(), mockcfg, pep_exitout=(0, b'')):
            output = dnf_ci.api.pep8_isolated(tempfile.gettempdir(), mockcfg)
        self.assertEqual(output, b'', 'incorrect output')
        self.assertEqual(
            self.cfg2packages[mockcfg], {'python-pep8', 'python3-pep8'},
            'not installed')

    def test_pep8_isolated_failing(self):
        """Test running with failing checks.

        :raise AssertionError: if the test fails

        """
        cwd = tempfile.gettempdir()
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        output = (
            cwd.encode() + b':1:80: E501 line too long (80 > 79 characters)\n')
        with self.assertRaises(subprocess.CalledProcessError) as context:
            with self.patch(cwd, mockcfg, pep_exitout=(1, output)):
                dnf_ci.api.pep8_isolated(cwd, mockcfg)
        self.assertEqual(
            context.exception.returncode, 1, 'incorrect status')
        self.assertEqual(
            context.exception.output, output * 2, 'incorrect output')
        self.assertEqual(
            self.cfg2packages[mockcfg], {'python-pep8', 'python3-pep8'},
            'not installed')

    def test_pyflakes_isolated_successful(self):  # pylint: disable=C0103
        """Test running with successful checks.

        :raise AssertionError: if the test fails

        """
        cwd = tempfile.gettempdir()
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        with self.patch(cwd, mockcfg, flakes_exitout=(0, b'')):
            output = dnf_ci.api.pyflakes_isolated(cwd, mockcfg)
        self.assertEqual(output, b'', 'incorrect output')
        self.assertEqual(
            self.cfg2packages[mockcfg], {'pyflakes', 'python3-pyflakes'},
            'not installed')

    def test_pyflakes_isolated_failing(self):
        """Test running with failing checks.

        :raise AssertionError: if the test fails

        """
        cwd = tempfile.gettempdir()
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        output = cwd.encode() + b":1: 'unittest' imported but unused\n"
        with self.assertRaises(subprocess.CalledProcessError) as context:
            with self.patch(cwd, mockcfg, flakes_exitout=(1, output)):
                dnf_ci.api.pyflakes_isolated(cwd, mockcfg)
        self.assertEqual(
            context.exception.returncode, 1, 'incorrect status')
        self.assertEqual(
            context.exception.output, output * 2, 'incorrect output')
        self.assertEqual(
            self.cfg2packages[mockcfg], {'pyflakes', 'python3-pyflakes'},
            'not installed')

    def test_pylint_isolated_successful(self):
        """Test running with successful checks.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        patcher = self.patch(
            tempfile.gettempdir(), mockcfg, lint_reldns=['d1', 'd2'],
            lint_exitout=(0, b''))
        with patcher:
            output = dnf_ci.api.pylint_isolated(
                ['d1', 'd2'], tempfile.gettempdir(), ['p1', 'p2'], mockcfg)
        self.assertEqual(output, b'', 'incorrect output')
        self.assertEqual(
            self.cfg2packages[mockcfg],
            {'p1', 'p2', 'pylint', 'python3-pylint'},
            'not installed')

    def test_pylint_isolated_failing(self):
        """Test running with failing checks.

        :raise AssertionError: if the test fails

        """
        mockcfg = os.path.join(tempfile.gettempdir(), 'root.cfg')
        output = (
            tempfile.gettempdir().encode() +
            b'/d1:1: [E0001(syntax-error), ] invalid syntax\n')
        patcher = self.patch(
            tempfile.gettempdir(), mockcfg, lint_reldns=['d1', 'd2'],
            lint_exitout=(1, output))
        with self.assertRaises(subprocess.CalledProcessError) as context:
            with patcher:
                dnf_ci.api.pylint_isolated(
                    ['d1', 'd2'], tempfile.gettempdir(), ['p1', 'p2'], mockcfg)
        self.assertEqual(
            context.exception.returncode, 1, 'incorrect status')
        self.assertEqual(
            context.exception.output, output * 2, 'incorrect output')
        self.assertEqual(
            self.cfg2packages[mockcfg],
            {'p1', 'p2', 'pylint', 'python3-pylint'},
            'not installed')


if __name__ == '__main__':
    unittest.main()
