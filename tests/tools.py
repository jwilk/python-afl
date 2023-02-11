# encoding=UTF-8

# Copyright © 2013-2022 Jakub Wilk <jwilk@jwilk.net>
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

import contextlib
import functools
import os
import re
import shutil
import subprocess as ipc
import sys
import tempfile
import traceback
import unittest
import warnings

try:
    # Python >= 3.3
    from shlex import quote as sh_quote
except ImportError:
    # Python << 3.3
    from pipes import quote as sh_quote  # pylint: disable=deprecated-module

SkipTest = unittest.SkipTest

def assert_fail(msg):
    assert_true(False, msg=msg)  # pylint: disable=redundant-unittest-assert

tc = unittest.TestCase('__hash__')

assert_equal = tc.assertEqual

assert_in = tc.assertIn

assert_not_equal = tc.assertNotEqual

assert_true = tc.assertTrue

assert_raises = tc.assertRaises

# pylint: disable=no-member
if sys.version_info >= (3,):
    assert_raises_regex = tc.assertRaisesRegex
else:
    assert_raises_regex = tc.assertRaisesRegexp
# pylint: enable=no-member

# pylint: disable=no-member
if sys.version_info >= (3,):
    assert_regex = tc.assertRegex
else:
    assert_regex = tc.assertRegexpMatches
# pylint: enable=no-member

if sys.version_info >= (3,):
    assert_warns_regex = tc.assertWarnsRegex  # pylint: disable=no-member
else:
    @contextlib.contextmanager
    def assert_warns_regex(exc_type, regex):
        with warnings.catch_warnings(record=True) as wlog:
            warnings.simplefilter('always', exc_type)
            yield
        firstw = None
        for warning in wlog:
            w = warning.message
            if not isinstance(w, exc_type):
                continue
            if firstw is None:
                firstw = w
            if re.search(regex, str(w)):
                return
        if firstw is None:
            assert_fail(msg='{exc} not triggered'.format(exc=exc_type.__name__))
        else:
            assert_fail(msg='{exc!r} does not match {re!r}'.format(exc=str(firstw), re=regex))

class IsolatedException(Exception):
    pass

def _n_relevant_tb_levels(tb):
    n = 0
    while tb and '__unittest' not in tb.tb_frame.f_globals:
        n += 1
        tb = tb.tb_next
    return n

def clean_environ():
    for key in list(os.environ):
        if key.startswith('PYTHON_AFL_'):
            del os.environ[key]
    os.environ['AFL_SKIP_CPUFREQ'] = '1'
    os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
    os.environ['AFL_NO_AFFINITY'] = '1'
    os.environ['AFL_ALLOW_TMP'] = '1'  # AFL >= 2.48b
    os.environ['PWD'] = '//' + os.getcwd()  # poor man's AFL_ALLOW_TMP for AFL << 2.48b

def require_commands(*cmds):
    PATH = os.environ.get('PATH', os.defpath)
    PATH = PATH.split(os.pathsep)
    for cmd in cmds:
        for dir in PATH:
            path = os.path.join(dir, cmd)
            if os.access(path, os.X_OK):
                break
        else:
            if cmd == 'ps':
                cmd = 'ps(1)'
                reason = 'procps installed'
            elif cmd.startswith('afl-'):
                reason = 'AFL installed'
            else:
                reason = 'PATH set correctly'
            raise RuntimeError('{cmd} not found; is {reason}?'.format(cmd=cmd, reason=reason))

def run(cmd, stdin='', xstatus=0):
    cmd = list(cmd)
    child = ipc.Popen(  # pylint: disable=consider-using-with
        cmd,
        stdin=ipc.PIPE,
        stdout=ipc.PIPE,
        stderr=ipc.PIPE,
        preexec_fn=clean_environ,
    )
    (stdout, stderr) = child.communicate(stdin)
    if child.returncode != xstatus:
        print('command:', '\n ', *map(sh_quote, cmd))
        def xprint(**kwargs):
            [(name, out)] = kwargs.items()  # pylint: disable=unbalanced-tuple-unpacking,unbalanced-dict-unpacking
            if not out:
                return
            print()
            print(name, ':', sep='')
            if str is not bytes:
                out = out.decode('ASCII', 'replace')
            for line in out.splitlines():
                print(' ', line)
        xprint(stdout=stdout)
        xprint(stderr=stderr)
        raise ipc.CalledProcessError(child.returncode, cmd[0])
    return (stdout, stderr)

def fork_isolation(f):

    EXIT_EXCEPTION = 101
    EXIT_SKIP_TEST = 102

    exit = os._exit  # pylint: disable=redefined-builtin,protected-access
    # sys.exit() can't be used here, because the test harness
    # catches all exceptions, including SystemExit

    # pylint:disable=consider-using-sys-exit

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        readfd, writefd = os.pipe()
        pid = os.fork()
        if pid == 0:
            # child:
            os.close(readfd)
            try:
                f(*args, **kwargs)
            except SkipTest as exc:
                s = str(exc)
                if not isinstance(s, bytes):
                    s = s.encode('UTF-8')
                with os.fdopen(writefd, 'wb') as fp:
                    fp.write(s)
                exit(EXIT_SKIP_TEST)
            except Exception:  # pylint: disable=broad-except
                exctp, exc, tb = sys.exc_info()
                s = traceback.format_exception(exctp, exc, tb, _n_relevant_tb_levels(tb))
                s = str.join('', s)
                if not isinstance(s, bytes):
                    s = s.encode('UTF-8')
                del tb
                with os.fdopen(writefd, 'wb') as fp:
                    fp.write(s)
                exit(EXIT_EXCEPTION)
            exit(0)
        else:
            # parent:
            os.close(writefd)
            with os.fdopen(readfd, 'rb') as fp:
                msg = fp.read()
            if not isinstance(msg, str):
                msg = msg.decode('UTF-8')
            msg = msg.rstrip('\n')
            pid, status = os.waitpid(pid, 0)
            if status == (EXIT_EXCEPTION << 8):
                raise IsolatedException('\n\n' + msg)
            elif status == (EXIT_SKIP_TEST << 8):
                raise SkipTest(msg)
            elif status == 0 and msg == '':
                pass
            else:
                raise RuntimeError('unexpected isolated process status {0}'.format(status))

    # pylint:enable=consider-using-sys-exit

    return wrapper

@contextlib.contextmanager
def tempdir():
    d = tempfile.mkdtemp(prefix='python-afl.')
    try:
        yield d
    finally:
        shutil.rmtree(d)

__all__ = [
    'SkipTest',
    'assert_equal',
    'assert_in',
    'assert_not_equal',
    'assert_raises',
    'assert_raises_regex',
    'assert_regex',
    'assert_true',
    'assert_warns_regex',
    'fork_isolation',
    'require_commands',
    'run',
    'tempdir',
]

# vim:ts=4 sts=4 sw=4 et
