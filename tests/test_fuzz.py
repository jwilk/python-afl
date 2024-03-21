# encoding=UTF-8

# Copyright © 2015-2024 Jakub Wilk <jwilk@jwilk.net>
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
    from pipes import quote as shell_quote  # pylint: disable=deprecated-module

try:
    # Python 3
    from itertools import izip_longest as zip_longest
except ImportError:
    # Python 2
    from itertools import zip_longest

from .tools import (
    SkipTest,
    assert_true,
    clean_environ,
    require_commands,
    tempdir,
)

here = os.path.dirname(__file__)

token = base64.b64encode(os.urandom(8))
if not isinstance(token, str):
    token = token.decode('ASCII')

def vcmp(v1, v2):
    '''
    cmp()-style version comparison
    '''
    v1 = v1.split('.')
    v2 = v2.split('.')
    for c1, c2 in zip_longest(v1, v2, fillvalue=0):
        c1 = int(c1)
        c2 = int(c2)
        if c1 > c2:
            return 1
        elif c1 < c2:
            return -1
    return 0

def get_afl_version():
    require_commands('afl-fuzz')
    child = ipc.Popen(['afl-fuzz'], stdout=ipc.PIPE)  # pylint: disable=consider-using-with
    version = child.stdout.readline()
    child.stdout.close()
    child.wait()
    if str is not bytes:
        version = version.decode('ASCII')
    version = re.sub(r'\x1B\[[^m]+m', '', version)
    match = re.match(r'^afl-fuzz[+\s]+([0-9.]+)[a-z]?\b', version)
    if match is None:
        raise RuntimeError('could not parse AFL version')
    return match.group(1)

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

def __test_fuzz(workdir, target, dumb=False):
    require_commands('py-afl-fuzz', 'afl-fuzz')
    input_dir = workdir + '/in'
    output_dir = workdir + '/out'
    os.mkdir(input_dir)
    os.mkdir(output_dir)
    with open(input_dir + '/in', 'wb') as file:
        file.write(b'0')
    have_crash = False
    have_paths = False
    n_paths = 0
    with open('/dev/null', 'wb') as devnull:
        with open(workdir + '/stdout', 'wb') as stdout:
            cmdline = ['py-afl-fuzz', '-i', input_dir, '-o', output_dir, '--', sys.executable, target, token]
            if dumb:
                cmdline[1:1] = ['-n']
            print('$ ' + str.join(' ', map(shell_quote, cmdline)))
            afl = ipc.Popen(  # pylint: disable=consider-using-with
                cmdline,
                stdout=stdout,
                stdin=devnull,
                preexec_fn=clean_environ,
            )
    try:
        timeout = 10
        while timeout > 0:
            if afl.poll() is not None:
                break
            for ident in '', 'default':
                inst_out_dir = output_dir + '/' + ident
                crash_dir = inst_out_dir + '/crashes'
                queue_dir = inst_out_dir + '/queue'
                if os.path.isdir(queue_dir):
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
    require_commands('ps')
    try:
        yield
    finally:
        ps = ipc.Popen(['ps', 'ax'], stdout=ipc.PIPE)  # pylint: disable=consider-using-with
        strays = []
        for line in ps.stdout:
            if not isinstance(line, str):
                line = line.decode('ASCII', 'replace')
            if token in line:
                strays += [line]
        if strays:
            warnings.warn('stray process{es} left behind:\n{ps}'.format(
                es=('' if len(strays) == 1 else 'es'),
                ps=str.join('', strays)
            ), category=RuntimeWarning)
            for line in strays:
                pid = int(line.split()[0])
                os.kill(pid, signal.SIGKILL)
        ps.wait()

def _test_fuzz(target, dumb=False):
    with stray_process_cleanup():
        with tempdir() as workdir:
            __test_fuzz(
                workdir=workdir,
                target=os.path.join(here, target),
                dumb=dumb,
            )

def test_fuzz_nonpersistent():
    _test_fuzz('target.py')

def test_fuzz_persistent():
    _test_fuzz('target_persistent.py')

def _maybe_skip_fuzz_dumb():
    if vcmp(get_afl_version(), '1.95') < 0:
        raise SkipTest('afl-fuzz >= 1.95b is required')

def test_fuzz_dumb_nonpersistent():
    _maybe_skip_fuzz_dumb()
    _test_fuzz('target.py', dumb=True)

def test_fuzz_dumb_persistent():
    _maybe_skip_fuzz_dumb()
    _test_fuzz('target_persistent.py', dumb=True)

# vim:ts=4 sts=4 sw=4 et
