# encoding=UTF-8

# Copyright © 2015 Jakub Wilk <jwilk@jwilk.net>
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

import glob
import os
import shutil
import subprocess as ipc
import sys
import tempfile
import time

from nose import SkipTest
from nose.tools import assert_true

here = os.path.dirname(__file__)
target = here + '/target.py'

def test_fuzz():
    tmpdir = tempfile.mkdtemp(prefix='python-afl.')
    try:
        _test_fuzz(tmpdir)
    finally:
        shutil.rmtree(tmpdir)

def sleep(n):
    time.sleep(n)
    return n

def check_core_pattern():
    if not sys.platform.startswith('linux'):
        return
    try:
        file = open('/proc/sys/kernel/core_pattern', 'rb')
    except OSError:
        return
    with file:
        pattern = file.read()
        if str != bytes:
            pattern = pattern.decode('ASCII', 'replace')
        if pattern.startswith('|'):
            raise SkipTest('/proc/sys/kernel/core_pattern = ' + pattern)

def _test_fuzz(workdir):
    check_core_pattern()
    input_dir = workdir + '/in'
    output_dir = workdir + '/out'
    os.mkdir(input_dir)
    os.mkdir(output_dir)
    with open(input_dir + '/in', 'w') as file:
        file.write('0')
    crash_dir = output_dir + '/crashes'
    queue_dir = output_dir + '/queue'
    have_crash = False
    have_paths = False
    def setup_env():
        os.environ['AFL_SKIP_CPUFREQ'] = '1'
    with open('/dev/null', 'wb') as devnull:
        with open(workdir + '/stdout', 'wb') as stdout:
            afl = ipc.Popen(
                ['py-afl-fuzz', '-i', input_dir, '-o', output_dir, '--', sys.executable, target],
                stdout=stdout,
                stdin=devnull,
                preexec_fn=setup_env,
            )
    try:
        timeout = 10
        while timeout > 0:
            if afl.poll() is not None:
                break
            have_crash = len(glob.glob(crash_dir + '/id:*')) >= 1
            have_paths = len(glob.glob(queue_dir + '/id:*')) >= 2
            if have_crash and have_paths:
                break
            timeout -= sleep(0.1)
        if afl.returncode is None:
            afl.terminate()
            afl.wait()
    except:
        afl.kill()
        raise
    with open(workdir + '/stdout', 'rb') as file:
        stdout = file.read()
        if str != bytes:
            stdout = stdout.decode('ASCII', 'replace')
        print(stdout)
    assert_true(have_crash, "target program didn't crash")
    assert_true(have_paths, "target program didn't produce two distinct paths")

# vim:ts=4 sts=4 sw=4 et
