# encoding=UTF-8

# Copyright © 2015-2022 Jakub Wilk <jwilk@jwilk.net>
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

def run_afl_cmin(input, xoutput, crashes_only=False):
    require_commands('py-afl-cmin', 'afl-cmin')
    input = sorted(input)
    xoutput = sorted(xoutput)
    with tempdir() as workdir:
        indir = '//{dir}/in'.format(dir=workdir)
        outdir = '//{dir}/out'.format(dir=workdir)
        for dir in [indir, outdir]:
            os.mkdir(dir)
        for n, blob in enumerate(input):
            path = '{dir}/{n}'.format(dir=indir, n=n)
            with open(path, 'wb') as file:
                file.write(blob)
        cmdline = ['py-afl-cmin', '-i', indir, '-o', outdir, '--', sys.executable, target]
        if crashes_only:
            cmdline[1:1] = ['-C']
        run(cmdline)
        output = []
        for n in os.listdir(outdir):
            path = '{dir}/{n}'.format(dir=outdir, n=n)
            with open(path, 'rb') as file:
                blob = file.read()
                output += [blob]
        output.sort()
        assert_equal(xoutput, output)

def test():
    run_afl_cmin([
        b'0' * 6, b'0',
        b'X' * 7, b'1',
        b'\xCF\x87',
    ], [
        b'0',
        b'1',
    ])

def test_crashes_only():
    run_afl_cmin([
        b'0' * 6, b'0',
        b'X' * 7, b'1',
        b'\xCF\x87',
    ], [
        b'\xCF\x87',
    ], crashes_only=True)

# vim:ts=4 sts=4 sw=4 et
