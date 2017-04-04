# encoding=UTF-8

# Copyright © 2015-2017 Jakub Wilk <jwilk@jwilk.net>
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

import os
import signal

import afl

from .tools import (
    assert_equal,
    assert_raises_regex,
    fork_isolation,
)

def test_persistent():
    _test_persistent(None)
    _test_persistent(1, 1)
    _test_persistent(1, max=1)
    _test_persistent(42, 42)
    _test_persistent(42, max=42)

@fork_isolation
def _test_persistent(n, *args, **kwargs):
    os.environ['PYTHON_AFL_PERSISTENT'] = '1'
    n_max = 1000
    k = [0]
    def kill(pid, sig):
        assert_equal(pid, os.getpid())
        assert_equal(sig, signal.SIGSTOP)
        k[0] += 1
    os.kill = kill
    x = 0
    while afl.loop(*args, **kwargs):
        x += 1
        if x == n_max:
            break
    if n is None:
        n = n_max
    assert_equal(x, n)
    assert_equal(k[0], n - 1)

def test_docile():
    _test_docile()
    _test_docile(1)
    _test_docile(max=1)
    _test_docile(42)
    _test_docile(max=42)

@fork_isolation
def _test_docile(*args, **kwargs):
    os.environ.pop('PYTHON_AFL_PERSISTENT', None)
    x = 0
    while afl.loop(*args, **kwargs):
        x += 1
    assert_equal(x, 1)

@fork_isolation
def test_double_init():
    afl.init()
    with assert_raises_regex(RuntimeError, '^AFL already initialized$'):
        while afl.loop():
            pass

# vim:ts=4 sts=4 sw=4 et
