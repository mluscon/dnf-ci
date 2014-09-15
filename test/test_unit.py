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
from __future__ import unicode_literals

import contextlib
import tempfile
import unittest.mock

import dnf_ci


class _GitStub(object):  # pylint: disable=too-few-public-methods

    """Testing stub of the "git" executable.

    :ivar difffiles_repo2status: exit status of "git diff-files" command for
       each repository
    :type difffiles_repo2status: dict[str, int]
    :ivar diffindex_repo2statuses: exit statuses of "git diff-index" command
       for each index update and repository
    :type diffindex_repo2statuses: dict[str, list[int]]

    """

    def __init__(self, difffiles, diffindex):
        """Initialize the stub.

        :param difffiles_repo2status: exit status of "git diff-files" command
           for each repository
        :type difffiles_repo2status: dict[str, int]
        :param diffindex_repo2statuses: exit statuses of "git diff-index"
           command for each index update and repository
        :type diffindex_repo2statuses: dict[str, list[int]]

        """
        self.difffiles_repo2status = difffiles
        self.diffindex_repo2statuses = diffindex

    def __call__(self, args):
        """Call the executable with command line arguments.

        :param args: the arguments
        :type args: list[str]
        :return: the exit status
        :rtype: int

        """
        if args[3] == 'update-index':
            statuses = self.diffindex_repo2statuses[args[2]]
            if len(statuses) > 1:
                statuses.pop(0)
        elif args[3] == 'diff-files':
            return self.difffiles_repo2status[args[2]]
        elif args[3] == 'diff-index':
            return self.diffindex_repo2statuses[args[2]][0]


class GitExecutableTestCase(unittest.TestCase):  # pylint: disable=R0904

    """Git executable test case."""

    @staticmethod
    @contextlib.contextmanager
    def patch(repository, difffiles=0, diffindex=None):
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
        files, index = {repository: difffiles}, {repository: diffindex or [0]}
        with unittest.mock.patch('subprocess.call', _GitStub(files, index)):
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


if __name__ == '__main__':
    unittest.main()
