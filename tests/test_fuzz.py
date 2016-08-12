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

from __future__ import print_function

import base64
import contextlib
import distutils.version
import glob
import os
import re
import signal
import subprocess as ipc
import sys
import time
import warnings

try:
    # Python >= 3.3
    from shlex import quote as shell_quote
except ImportError:
    # Python << 3.3
    from pipes import quote as shell_quote

from .tools import (
    SkipTest,
    assert_true,
    tempdir,
)

here = os.path.dirname(__file__)

token = base64.b64encode(os.urandom(8))
if not isinstance(token, str):
    token = token.decode('ASCII')

def get_afl_version():
    child = ipc.Popen(['afl-fuzz'], stdout=ipc.PIPE)
    version = child.stdout.readline()
    child.stdout.close()
    child.wait()
    if str is not bytes:
        version = version.decode('ASCII')
    version = re.sub(r'\x1b\[[^m]+m', '', version)
    match = re.match(r'^afl-fuzz\s+([0-9.]+)b?\b', version)
    version = match.group(1)
    return distutils.version.StrictVersion(version)

def sleep(n):
    time.sleep(n)
    return n

def check_core_pattern():
    with open('/proc/sys/kernel/core_pattern', 'rb') as file:
        pattern = file.read()
        if str is not bytes:
            pattern = pattern.decode('ASCII', 'replace')
        pattern = pattern.rstrip('\n')
        if pattern.startswith('|'):
            raise SkipTest('/proc/sys/kernel/core_pattern = ' + pattern)

def _test_fuzz(workdir, target, dumb=False):
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
    n_paths = 0
    def setup_env():
        os.environ['AFL_SKIP_CPUFREQ'] = '1'
        os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
        os.environ['AFL_NO_AFFINITY'] = '1'
    with open('/dev/null', 'wb') as devnull:
        with open(workdir + '/stdout', 'wb') as stdout:
            cmdline = ['py-afl-fuzz', '-i', input_dir, '-o', output_dir, '--', sys.executable, target, token]
            if dumb:
                cmdline[1:1] = ['-n']
            print('$ ' + ' '.join(shell_quote(arg) for arg in cmdline))
            afl = ipc.Popen(
                cmdline,
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
            n_paths = len(glob.glob(queue_dir + '/id:*'))
            have_paths = (n_paths == 1) if dumb else (n_paths >= 2)
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
        if str is not bytes:
            stdout = stdout.decode('ASCII', 'replace')
        print(stdout)
    if not have_crash and '/proc/sys/kernel/core_pattern' in stdout:
        check_core_pattern()
    assert_true(have_crash, "target program didn't crash")
    assert_true(have_paths, 'target program produced {n} distinct paths'.format(n=n_paths))

@contextlib.contextmanager
def stray_process_cleanup():
    # afl-fuzz doesn't always kill the target process:
    # https://groups.google.com/d/topic/afl-users/E37s4YDti7o
    try:
        yield
    finally:
        ps = ipc.Popen(['ps', 'ax'], stdout=ipc.PIPE)
        strays = []
        for line in ps.stdout:
            if not isinstance(line, str):
                line = line.decode('ASCII', 'replace')
            if token in line:
                strays += [line]
        if strays:
            warnings.warn('stray process{es} left behind:\n{ps}'.format(
                es=('' if len(strays) == 1 else 'es'),
                ps=''.join(strays)
            ), category=RuntimeWarning)
            for line in strays:
                pid = int(line.split()[0])
                os.kill(pid, signal.SIGKILL)
        ps.wait()

def test_fuzz(dumb=False):
    def t(target):
        with stray_process_cleanup():
            with tempdir() as workdir:
                _test_fuzz(
                    workdir=workdir,
                    target=os.path.join(here, target),
                    dumb=dumb,
                )
    yield t, 'target.py'
    yield t, 'target_persistent.py'

def test_fuzz_dumb():
    if get_afl_version() < '1.95':
        def skip():
            raise SkipTest('afl-fuzz >= 1.95b is required')
    else:
        skip = False
    for t in test_fuzz(dumb=True):
        yield skip or t

# vim:ts=4 sts=4 sw=4 et
