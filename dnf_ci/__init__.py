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
from __future__ import unicode_literals

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
