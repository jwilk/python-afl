# encoding=UTF-8

# Copyright © 2014, 2015 Jakub Wilk <jwilk@jwilk.net>
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

'''
American fuzzy lop instrumentation for Python
'''

import os
import signal
import struct
import sys
import warnings

# These constants must be kept in sync with afl-fuzz:
DEF SHM_ENV_VAR = '__AFL_SHM_ID'
DEF FORKSRV_FD = 198
DEF MAP_SIZE_POW2 = 16
DEF MAP_SIZE = 1 << MAP_SIZE_POW2

from cpython.exc cimport PyErr_SetFromErrno
from libc cimport errno

cdef extern from 'sys/shm.h':
    unsigned char *shmat(int shmid, void *shmaddr, int shmflg)

cdef unsigned char *afl_area = NULL
cdef unsigned long prev_location = 0

class AflError(Exception):
    pass

def trace(frame, event, arg):
    global prev_location
    cdef unsigned long location, offset
    location = hash((frame.f_code.co_filename, frame.f_lineno))
    location %= MAP_SIZE
    offset = location ^ prev_location
    prev_location = location // 2
    afl_area[offset] += 1
    # TODO: make it configurable which modules are instrumented, and which are not
    return trace

cdef int except_signal_id = 0
cdef object except_signal_name
except_signal_name = os.getenv('PYTHON_AFL_SIGNAL', 'SIGUSR1') or '0'
if except_signal_name.isdigit():
    except_signal_id = int(except_signal_name)
else:
    if except_signal_name[:3] != 'SIG':
        except_signal_name = 'SIG' + except_signal_name
    except_signal_id = getattr(signal, except_signal_name)

def excepthook(tp, value, traceback):
    os.kill(os.getpid(), except_signal_id)

def start():
    cdef int use_forkserver = 1
    global afl_area
    afl_shm_id = os.getenv(SHM_ENV_VAR)
    if afl_shm_id is None:
        warnings.warn('no AFL environment')
        return
    if os.getenv('PYTHONHASHSEED', '') != '0':
        raise AflError('PYTHONHASHSEED != 0')
    afl_shm_id = int(afl_shm_id)
    afl_area = shmat(afl_shm_id, NULL, 0)
    if afl_area == <void*> -1:
        PyErr_SetFromErrno(OSError)
    try:
        os.write(FORKSRV_FD + 1, b'\0\0\0\0')
    except OSError as exc:
        if exc.errno == errno.EBADF:
            use_forkserver = 0
        else:
            raise
    while use_forkserver:
        if not os.read(FORKSRV_FD, 4):
            sys.exit()
        pid = os.fork()
        if not pid:
            # child:
            break
        # parent:
        os.write(FORKSRV_FD + 1, struct.pack('I', pid))
        (pid, status) = os.waitpid(pid, os.WUNTRACED)
        os.write(FORKSRV_FD + 1, struct.pack('I', status))
    if use_forkserver:
        os.close(FORKSRV_FD)
        os.close(FORKSRV_FD + 1)
    if except_signal_id != 0:
        sys.excepthook = excepthook
    if not os.getenv('PYTHON_AFL_DUMB'):
        sys.settrace(trace)

__all__ = ['start', 'AflError']

# vim:ts=4 sts=4 sw=4 et
