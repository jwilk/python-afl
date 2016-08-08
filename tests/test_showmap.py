# encoding=UTF-8

# Copyright © 2015-2016 Jakub Wilk <jwilk@jwilk.net>
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
import subprocess as ipc
import sys

from .tools import (
    assert_equal,
    assert_not_equal,
    tempdir,
)

here = os.path.dirname(__file__)
target = here + '/target.py'

def run(cmd, stdin='', env=None, xstatus=0):
    child = ipc.Popen(
        list(cmd),
        stdin=ipc.PIPE,
        stdout=ipc.PIPE,
        stderr=ipc.PIPE,
        env=(dict(os.environ, **env) if env else None),
    )
    (stdout, stderr) = child.communicate(stdin)
    if child.returncode != xstatus:
        if str is not bytes:
            stderr = stderr.decode('ASCII', 'replace')
        print(stderr)
        raise ipc.CalledProcessError(child.returncode, cmd[0])
    return (stdout, stderr)

def run_afl_showmap(stdin, env=None, xstdout=None, xstatus=0):
    with tempdir() as workdir:
        outpath = workdir + '/out'
        (stdout, stderr) = run(
            ['afl-showmap', '-o', outpath, sys.executable, target],
            stdin=stdin,
            env=env,
            xstatus=xstatus,
        )
        del stderr  # make pylint happy
        if xstdout is not None:
            assert_equal(stdout, xstdout)
        with open(outpath, 'r') as file:
            return file.read()

def test_diff():
    out1 = run_afl_showmap(b'0', xstdout=b'Looks like a zero to me!\n')
    out2 = run_afl_showmap(b'1', xstdout=b'A non-zero value? How quaint!\n')
    assert_not_equal(out1, out2)

def test_exception():
    out = run_afl_showmap(b'\xff',
        env=dict(PYTHON_AFL_SIGNAL='SIGUSR1'),
        xstatus=2,
    )
    assert_not_equal(out, b'')

# vim:ts=4 sts=4 sw=4 et
