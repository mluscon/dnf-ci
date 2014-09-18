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

"""Entry point to building, distributing, and installing the project.

The current working directory must contain the readable "README" file encoded
in UTF-8 and the "dnf_ci" package directory. The "dnf_ci" and "test" packages
must be importable.

"""


from __future__ import absolute_import
from __future__ import unicode_literals

import codecs
import sys

import docutils.core
import docutils.nodes
import setuptools


def _first_paragraph(restructuredtext):
    r"""Return the first paragraph of a text.

    :param restructuredtext: the ReStructuredText-formatted text
    :type restructuredtext: str
    :return: the paragraph
    :rtype: str

    >>> _first_paragraph(u'Lorem ipsum\ndolor met amet.\n\n'
    ...                  u'This is a second paragraph.\n')
    'Lorem ipsum\ndolor met amet.'

    """
    settings = {'input_encoding': 'unicode'}
    doctree = docutils.core.publish_doctree(
        restructuredtext, settings_overrides=settings)
    index = doctree.first_child_matching_class(docutils.nodes.paragraph)
    paragraph_ = doctree[index]
    return paragraph_.rawsource


if __name__ == '__main__':
    with codecs.open('README', encoding='utf-8') as _file:
        README = _file.read()
    setuptools.setup(
        name='dnf-ci',
        version='1.0.0dev',
        author='Radek Holý',
        author_email='rholy@redhat.com',
        url='https://github.com/rholy/dnf-ci',
        license='Apache License, Version 2.0',
        description=_first_paragraph(README),
        long_description=README,
        keywords=['DNF', 'continuous integration'],
        classifiers=[
            'Development Status :: 2 - Pre-Alpha',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: ' +
            str(sys.version_info.major) + '.' + str(sys.version_info.minor),
            'Topic :: Software Development :: Build Tools',
            'Topic :: Software Development :: Quality Assurance',
            'Topic :: Software Development :: Testing'],
        setup_requires=['docutils', 'setuptools'],
        packages=['dnf_ci'],
        test_suite='test'
    )
