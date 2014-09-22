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

import codecs
import contextlib
import doctest
import importlib
import inspect
import os
import re
import subprocess
import sys
import tempfile
import unittest


TESTMODNAMES = {
    # some tools may walk packages recursively -- avoid that
    'dnf_ci.__init__',
    'setup',
    'test.__init__',
    'test.test_code',
    'test.test_unit'}


def _findsrcfile(name):
    """Find source file an importable non-built-in module.

    :param name: name of the module
    :type name: str
    :return: name of the source file
    :rtype: str

    """
    return inspect.getsourcefile(importlib.import_module(name))


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

    @staticmethod
    def apidoc(modnames, dirname):
        """Create Sphinx documentation sources for modules.

        :param modnames: names of the modules
        :type modnames: collections.abc.Iterable[str]
        :param dirname: name of the writable sources directory
        :type dirname: str

        """
        rootname = lambda fname: os.path.splitext(os.path.basename(fname))[0]
        toc_fn = os.path.join(dirname, 'contents.rst')
        with codecs.open(toc_fn, 'w', encoding='utf_8') as tocfile:
            tocfile.write('.. toctree::\n')
            for modname in modnames:
                mod_fn = os.path.join(dirname, modname + '.rst')
                with codecs.open(mod_fn, 'w', encoding='utf_8') as modfile:
                    modfile.write(
                        modname + '\n' +
                        ('=' * len(modname)) + '\n'
                        '.. automodule:: ' + modname + '\n'
                        '    :members:\n'
                        '    :undoc-members:\n'
                        '    :private-members:\n'
                        '    :special-members:\n')
                tocfile.write('   ' + rootname(mod_fn) + '\n')
        conf_fn = os.path.join(dirname, 'conf.py')
        with codecs.open(conf_fn, 'w', encoding='utf_8') as conffile:
            conffile.write(
                'extensions = [\n'
                '    "sphinx.ext.autodoc",\n'
                '    "sphinx.ext.intersphinx"]\n'
                'nitpick_ignore = [\n'
                '    ("py:obj", "archive"),\n'
                '    ("py:obj", "chown"),\n'
                '    ("py:obj", "cmake"),\n'
                '    ("py:obj", "collections.abc.Iterable[str]"),\n'
                '    ("py:obj", "dict[str, int]"),\n'
                '    ("py:obj", "dict[str, list[int]]"),\n'
                '    ("py:obj", "dict[str, str]"),\n'
                '    ("py:obj", "dict[str, str] | None"),\n'
                '    ("py:obj", "dict[str, test.test_unit._Executable] | '
                'None"),\n'
                '    ("py:obj", "dict[str, tuple[int, bytes]]"),\n'
                '    ("py:obj", "'
                'dict[tuple[str, str, bool, str, str, str, bool], int]"),\n'
                '    ("py:obj", "difffiles_repo2status"),\n'
                '    ("py:obj", "diffindex_repo2statuses"),\n'
                '    ("py:obj", "dn2content"),\n'
                '    ("py:obj", "dn2exitout"),\n'
                '    ("py:obj", "dn2file"),\n'
                '    ("py:obj", "dn2group"),\n'
                '    ("py:obj", "dn2rev"),\n'
                '    ("py:obj", "dn2src"),\n'
                '    ("py:obj", "dn2tuple"),\n'
                '    ("py:obj", "failing"),\n'
                '    ("py:obj", "fn2content"),\n'
                '    ("py:obj", "fn2exe"),\n'
                '    ("py:obj", "fn2file"),\n'
                '    ("py:obj", "list[int] | None"),\n'
                '    ("py:obj", "list[str]"),\n'
                '    ("py:obj", "list[str] | None"),\n'
                '    ("py:obj", "mock"),\n'
                '    ("py:obj", "path_fn2exe"),\n'
                '    ("py:obj", "regex"),\n'
                '    ("py:obj", "repo2source"),\n'
                '    ("py:obj", "root2packages"),\n'
                '    ("py:obj", "root2subprocess"),\n'
                '    ("py:obj", "set[str]"),\n'
                '    ("py:obj", "stdout"),\n'
                '    ("py:obj", "str | None"),\n'
                '    ("py:obj", "streams"),\n'
                '    ("py:obj", "test.test_unit._ArchiveStub | None"),\n'
                '    ("py:obj", "test.test_unit._CmakeStub | None"),\n'
                '    ("py:obj", "test.test_unit._StandardStreamsStub | '
                'None"),\n'
                '    ("py:obj", "tuple2exit"),\n'
                '    ("py:obj", "tuple2exitout"),\n'
                '    ("py:obj", "tuple[int, bytes]")]\n'
                'intersphinx_mapping = {\n'
                '    "python":\n'
                '        ("http://docs.python.org/' +
                str(sys.version_info[0]) + '.' + str(sys.version_info[1]) +
                '/", None)}\n')

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

    def assert_stdout(self, cmd, regex, msg=None):
        """Assert that a command's standard output matches a reg. expression.

        :param cmd: the command line vector which returns zero code
        :type cmd: list[str]
        :param regex: the regular expression
        :type regex: regex
        :param msg: error message
        :type msg: str | None
        :raise OSError: if the command cannot be executed
        :raise AssertionError: if the assertion fails

        """
        msg_ = self._formatMessage(msg, 'standard output mismatch')
        self.assertRegex(subprocess.check_output(cmd), regex, msg_)

    def test_clonedigger(self):
        """Test with Clone Digger.

        :raise unittest.SkipTest: if Clone Digger is not available
        :raise AssertionError: if the test fails

        """
        # Do not use the API to avoid trouble with incompatible licenses.
        cmd = ['clonedigger', '--no-recursion', '--output=clonedigger.html',
               '--force'] + [_findsrcfile(name) for name in TESTMODNAMES]
        regex = re.compile(
            b'^(Parsing  .+ \\.\\.\\. done\n)+\\d+ sequences\naverage '
            b'sequence length: \\d+\\.\\d+\nmaximum sequence length: \\d+\n'
            b'Number of statements:  \\d+\nCalculating size for each statement'
            b'\\.\\.\\. done\nBuilding statement hash\\.\\.\\. done\nNumber '
            b'of different hash values:  \\d+\nBuilding patterns\\.\\.\\. \\'
            b'd+ patterns were discovered\nChoosing pattern for each statement'
            b'\\.\\.\\. done\nFinding similar sequences of statements\\.\\.\\.'
            b' \\d+  sequences were found\nRefining candidates\\.\\.\\. 0 '
            b'clones were found\nRemoving dominated clones\\.\\.\\. 0 clones '
            b'were removed\n$')
        with self.skip_oserror('Clone Digger unavailable'):
            self.assert_stdout(cmd, regex, 'incorrect number of clones')

    def test_mccabe(self):
        """Test with McCabe complexity checker.

        :raise unittest.SkipTest: if McCabe complexity checker is not available
        :raise AssertionError: if the test fails

        """
        regex = re.compile(b'^$')
        for modname in TESTMODNAMES:
            filename = _findsrcfile(modname)
            # Do not use the API to be consistent throughout the module.
            cmd = ['mccabe', '--min=8', filename]
            with self.skip_oserror('McCabe complexity checker unavailable'):
                self.assert_stdout(cmd, regex, 'check failure: ' + filename)

    def test_pep257(self):
        """Test with pep257.

        :raise unittest.SkipTest: if pep257 is not available
        :raise AssertionError: if the test fails

        """
        # Do not use the API to be consistent throughout the module.
        cmd = ['pep257'] + [_findsrcfile(name) for name in TESTMODNAMES]
        with self.skip_oserror('pep257 unavailable'):
            self.assert_success(cmd, 'check failure')

    def test_pep8(self):
        """Test with pep8.

        :raise unittest.SkipTest: if pep8 is not available
        :raise AssertionError: if the test fails

        """
        # Do not use the API to be consistent throughout the module.
        cmd = ['pep8'] + [_findsrcfile(name) for name in TESTMODNAMES]
        with self.skip_oserror('pep8 unavailable'):
            self.assert_success(cmd, 'check failure')

    def test_pyflakes(self):
        """Test with Pyflakes.

        :raise unittest.SkipTest: if Pyflakes is not available
        :raise AssertionError: if the test fails

        """
        # Do not use the API to be consistent throughout the module.
        cmd = ['pyflakes'] + [_findsrcfile(name) for name in TESTMODNAMES]
        with self.skip_oserror('Pyflakes unavailable'):
            self.assert_success(cmd, 'check failure')

    def test_pylint(self):
        """Test with Pylint.

        :raise unittest.SkipTest: if Pylint is not available
        :raise AssertionError: if the test fails

        """
        # Do not use the API to avoid trouble with incompatible licenses.
        cmd = ['pylint', '--reports=n'] + list(TESTMODNAMES)
        with self.skip_oserror('Pylint unavailable'):
            self.assert_success(cmd, 'check failure')

    def test_sphinx(self):
        """Test with Sphinx.

        :raise unittest.SkipTest: if Sphinx is not available
        :raise AssertionError: if the test fails

        """
        with tempfile.TemporaryDirectory() as dirname:
            self.apidoc(TESTMODNAMES, dirname)
            # Do not use the API to be consistent throughout the module.
            cmd = ['sphinx-build', '-E', '-n', '-W', dirname, dirname]
            with self.skip_oserror('Sphinx unavailable'):
                self.assert_success(cmd, 'check failure')


if __name__ == '__main__':
    unittest.main()
