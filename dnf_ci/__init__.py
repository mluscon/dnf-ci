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

"""Package representing the software part of the project."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import fileinput
import itertools
import os
import subprocess


def uncommitted_changes(repository):
    """Check whether a Git repository contains uncommitted changes.

    "git" executable must be available.

    :param repository: name of the readable Git repository directory
    :type repository: str
    :return: uncommitted changes were found
    :rtype: bool

    """
    uicmd = ['git', '-C', repository, 'update-index', '-q', '--refresh']
    dfcmd = ['git', '-C', repository, 'diff-files', '--quiet']
    dicmd = ['git', '-C', repository, 'diff-index', '--quiet', 'HEAD', '--']
    subprocess.call(uicmd)
    return bool(subprocess.call(dfcmd) or subprocess.call(dicmd))


def clone(source, target):
    """Clone a Git repository.

    "git" executable must be available.

    :param source: name of the readable source Git repository
    :type source: str
    :param target: name of the writable non-existent target directory
    :type target: str

    """
    subprocess.call(['git', 'clone', '--quiet', source, target])


def build_dnf(source, destination, root):
    """Build a SRPM from a DNF Git repository.

    It is assumed that the workflow is to build DNF, run "package/archive",
    change the value of "gitrev" variable at the first line of
    "package/dnf.spec" to the output of "package/archive" and run Mock with
    the sources path set to "$HOME/rpmbuild/SOURCES". "cmake" and "mock"
    executables must be available. The root is initialized. This function
    cannot be called by a superuser.

    :param source: name of the readable and writable source Git repository
    :type source: str
    :param destination: name of a writable directory for the results
    :type destination: str
    :param root: name of a writable Mock root
    :type root: str

    """
    subprocess.call(['cmake', '.'], cwd=source)

    archive_fn = os.path.join(source, 'package', 'archive')
    revision = subprocess.check_output([archive_fn], cwd=source).decode()[:-1]

    spec_fn = os.path.join(source, 'package', 'dnf.spec')
    with fileinput.FileInput(spec_fn, inplace=True) as spec_file:
        next(spec_file)  # Skip the "gitrev" line.
        print('%global gitrev ' + revision)
        for line in spec_file:
            print(line[:-1])

    buildcmd = [
        'mock', '--quiet', '--root=' + root, '--resultdir=' + destination,
        '--no-cleanup-after', '--buildsrpm', '--spec=' + spec_fn,
        '--sources=' + os.path.expandvars('$HOME/rpmbuild/SOURCES')]
    subprocess.call(buildcmd)


def build_rpms(sources, destination, root):
    """Build the RPMs from SRPMs.

    "mockchain" executable must be available. *destination* must be readable by
    other users. This function cannot be called by a superuser.

    :param sources: names of the readable SRPM files
    :type sources: list[str]
    :param destination: name of a writable directory for the results
    :type destination: str
    :param root: name of a writable Mock root
    :type root: str
    :raise ValueError: if the build fails

    """
    cmd = ([
        'mockchain', '--root=' + root, '--localrepo=' + destination] + sources)
    if subprocess.call(cmd):
        raise ValueError('build failed')


def _mock_exec(root, cmdline, cwd='.', privileged=False):
    """Run a command non-interactively within a Mock root.

    "mock" executable must be available. The root must already be initialized.
    This function cannot be called by a superuser.

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
    cmd = [
        'mock', '--quiet', '--root=' + root, '--cwd=' + cwd, '--chroot',
        cmdline]
    if not privileged:
        cmd.insert(3, '--unpriv')
    return subprocess.check_output(cmd)


def _exec_isolation(cmdlines, cwd, dependencies, root):
    """Execute commands non-interactively in isolation.

    "mock" executable must be available. The root must already be initialized.
    Path /tmp/dnf-ci will be replaced.  This function cannot be called by a
    superuser.

    :param cmdlines: the commands to be run
    :type cmdlines: collections.abc.Iterable[str]
    :param cwd: name of a readable working directory that will be copied into
       the root
    :type cwd: str
    :param dependencies: required installable dependencies as an argument for
       "yum install" command
    :type dependencies: list[str]
    :param root: name of a writable Mock root
    :type root: str
    :return: joint standard output of the commands
    :rtype: bytes
    :raise subprocess.CalledProcessError: if any exit status is not zero

    """
    mockdn = '/tmp/dnf-ci'
    rmcmdl = 'rm --recursive --force ' + mockdn
    incmd = ['mock', '--quiet', '--root=' + root, '--install'] + dependencies
    cpcmd = ['mock', '--quiet', '--root=' + root, '--copyin', cwd, mockdn]
    chcmdl = 'chown --recursive :mockbuild ' + mockdn
    _mock_exec(root, rmcmdl, privileged=True)
    subprocess.call(incmd)
    subprocess.call(cpcmd)
    _mock_exec(root, chcmdl, privileged=True)
    err = subprocess.CalledProcessError(0, None, b'')
    for cmdline in cmdlines:
        try:
            err.output += _mock_exec(root, cmdline, mockdn)
        except subprocess.CalledProcessError as err_:
            if not err.returncode:
                err.cmd, err.returncode = err_.cmd, err_.returncode
            err.output += err_.output
    if err.returncode:
        raise err
    return err.output


def run_tests(tests, cwd, dependencies, root):
    """Run unit tests in isolation.

    "mock" executable must be available. The root must already be initialized.
    Path /tmp/dnf-ci will be replaced. The dependencies and Nose for both
    Python 2 and Python 3 will be installed into the root. This function cannot
    be called by a superuser.

    :param tests: the tests name to be run
    :type tests: str
    :param cwd: name of the readable working directory
    :type cwd: str
    :param dependencies: required installable dependencies as an argument for
       "yum install" command
    :type dependencies: list[str]
    :param root: name of a writable Mock root
    :type root: str
    :return: tests succeeded
    :rtype: bool

    """
    ncmd = (
        lambda version, test, locale='en_US.UTF-8', capture=True:
        'LANG=' + locale + ' LC_ALL=' + locale + ' nosetests-' + version +
        ' --quiet' + ('' if capture else ' --nocapture') + ' ' + test)
    tcmds = (
        [ncmd(version, tests),
         ncmd(version, tests, locale='cs_CZ.utf8'),
         ncmd(version, tests, capture=False)]
        for version in ['2.7', '3.4'])
    try:
        status, output = 0, _exec_isolation(
            itertools.chain.from_iterable(tcmds), cwd,
            dependencies + ['python-nose', 'python3-nose'], root)
    except subprocess.CalledProcessError as err:
        status, output = err.returncode, err.output
    print(output.decode())
    return not status


def pep8_isolated(dirname, root):
    """Run "pep8" non-interactively in isolation.

    "mock" executable must be available. The root must already be initialized.
    Path /tmp/dnf-ci will be replaced. Pep8 for both Python 2 and Python 3 will
    be installed into the root. This function cannot be called by a superuser.

    :param dirname: name of the directory to be checked
    :type dirname: str
    :param root: name of a writable Mock root
    :type root: str
    :return: standard output of the process
    :rtype: bytes
    :raise subprocess.CalledProcessError: if the exit status is not zero

    """
    return _exec_isolation(
        (exe + ' .' for exe in ['pep8', 'python3-pep8']), dirname,
        ['python-pep8', 'python3-pep8'], root)


def pyflakes_isolated(dirname, root):
    """Run "pyflakes" non-interactively in isolation.

    "mock" executable must be available. The root must already be initialized.
    Path /tmp/dnf-ci will be replaced. Pyflakes for both Python 2 and Python 3
    will be installed into the root. This function cannot be called by a
    superuser.

    :param dirname: name of the directory to be checked
    :type dirname: str
    :param root: name of a writable Mock root
    :type root: str
    :return: standard output of the process
    :rtype: bytes
    :raise subprocess.CalledProcessError: if the exit status is not zero

    """
    return _exec_isolation(
        (exe + ' .' for exe in ['pyflakes', 'python3-pyflakes']), dirname,
        ['pyflakes', 'python3-pyflakes'], root)
