#!/usr/bin/env python3.3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014  Radek Holý
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

"""Test quality of the source code.

All tested modules must be importable.

:var TESTMODNAMES: names of the readable modules to be tested
:type TESTMODNAMES: set[str]

"""


from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import doctest
import subprocess
import unittest


TESTMODNAMES = {
    'setup',
    'test.__init__',  # some tools may walk packages recursively -- avoid that
    'test.test_code'}


# noinspection PyUnusedLocal
def load_tests(loader, standard_tests, pattern):  # pylint: disable=W0613
    """Load a suite of all source code tests.

    :param loader: anything
    :type loader: object
    :param standard_tests: tests loaded by default
    :type standard_tests: unittest.TestSuite
    :param pattern: anything
    :type pattern: object
    :return: the tests
    :rtype: unittest.TestSuite

    """
    standard_tests.addTests(
        doctest.DocTestSuite(modname) for modname in TESTMODNAMES)
    return standard_tests


class TestCase(unittest.TestCase):  # pylint: disable=too-many-public-methods

    """Tests running selected code checkers."""

    @contextlib.contextmanager
    def skip_oserror(self, reason):
        """Return a context manager that skips potential :exc:`OSError`.

        :param reason: explanation of the skip
        :type reason: str
        :return: the context manager
        :rtype: contextmanager

        """
        try:
            yield
        except OSError:
            self.skipTest(reason)

    def assert_success(self, cmd, msg=None):
        """Assert that a command returns zero exit status.

        :param cmd: the command line vector
        :type cmd: list[str]
        :param msg: error message
        :type msg: str | None
        :raise OSError: if the command cannot be executed
        :raise AssertionError: if the assertion fails

        """
        msg_ = self._formatMessage(msg, 'non-zero exit status')
        self.assertEqual(subprocess.call(cmd), 0, msg_)

    def test_pylint(self):
        """Test with Pylint.

        :raise unittest.SkipTest: if Pylint is not available
        :raise AssertionError: if the test fails

        """
        # Do not use the API to avoid trouble with incompatible licenses.
        cmd = ['pylint', '--reports=n'] + list(TESTMODNAMES)
        with self.skip_oserror('Pylint unavailable'):
            self.assert_success(cmd, 'check failure')


if __name__ == '__main__':
    unittest.main()