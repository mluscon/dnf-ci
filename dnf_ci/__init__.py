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
