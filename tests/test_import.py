# encoding=UTF-8

# Copyright © 2015-2018 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import afl

from .tools import (
    assert_equal,
)

exports = [
    'init',
    'loop',
]

deprecated = [
    'start',
]

# pylint: disable=exec-used

def wildcard_import(mod):
    ns = {}
    exec('from {mod} import *'.format(mod=mod), {}, ns)
    return ns

def test_wildcard_import():
    ns = wildcard_import('afl')
    assert_equal(
        sorted(ns.keys()),
        sorted(exports)
    )

def test_dir():
    assert_equal(
        sorted(o for o in dir(afl) if not o.startswith('_')),
        sorted(exports + deprecated)
    )

# vim:ts=4 sts=4 sw=4 et
