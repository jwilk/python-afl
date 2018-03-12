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

import os
import sys

from .tools import (
    assert_equal,
    require_commands,
    run,
    tempdir,
)

here = os.path.dirname(__file__)
target = here + '/target.py'

def run_afl_tmin(input, xoutput, xstatus=0):
    require_commands('py-afl-tmin', 'afl-tmin')
    with tempdir() as workdir:
        inpath = workdir + '/in'
        with open(inpath, 'wb') as file:
            file.write(input)
        outpath = workdir + '/out'
        run(
            ['py-afl-tmin', '-i', inpath, '-o', outpath, '--', sys.executable, target],
            xstatus=xstatus,
        )
        with open(outpath, 'rb') as file:
            output = file.read()
        assert_equal(output, xoutput)

def test():
    run_afl_tmin(b'0' * 6, b'0')
    run_afl_tmin(b'X' * 7, b'X')

def test_exc():
    run_afl_tmin(b'\xCF\x87', b'\x87')

# vim:ts=4 sts=4 sw=4 et
