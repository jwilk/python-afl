# Copyright © 2014-2016 Jakub Wilk <jwilk@jwilk.net>
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

#cython: autotestdict=False
#cython: c_string_encoding=default

'''
American fuzzy lop fork server and instrumentation for pure-Python code
'''

__version__ = '0.5.5'

cdef object os, signal, struct, sys, warnings
import os
import signal
import struct
import sys
import warnings

# These constants must be kept in sync with afl-fuzz:
DEF SHM_ENV_VAR = b'__AFL_SHM_ID'
DEF FORKSRV_FD = 198
DEF MAP_SIZE_POW2 = 16
DEF MAP_SIZE = 1 << MAP_SIZE_POW2

from cpython.exc cimport PyErr_SetFromErrno
from libc cimport errno
from libc.stddef cimport size_t
from libc.stdint cimport uint32_t
from libc.stdlib cimport getenv
from libc.string cimport strlen

cdef extern from 'sys/shm.h':
    unsigned char *shmat(int shmid, void *shmaddr, int shmflg)

cdef unsigned char *afl_area = NULL
cdef unsigned int prev_location = 0

cdef inline unsigned int lhash(const char *key, size_t offset):
    # 32-bit Fowler–Noll–Vo hash function
    cdef size_t len = strlen(key)
    cdef uint32_t h = 0x811C9DC5
    while len > 0:
        h ^= <unsigned char> key[0];
        h *= 0x01000193
        len -= 1
        key += 1
    while offset > 0:
        h ^= <unsigned char> offset;
        h *= 0x01000193
        offset >>= 8
    return h

def _hash(key, offset):
    # This function is not a part of public API.
    # It is provided only to facilitate testing.
    return lhash(key, offset)

cdef object trace
def trace(frame, event, arg):
    global prev_location
    cdef unsigned int location, offset
    location = (
        lhash(frame.f_code.co_filename, frame.f_lineno)
        % MAP_SIZE
    )
    offset = location ^ prev_location
    prev_location = location // 2
    afl_area[offset] += 1
    # TODO: make it configurable which modules are instrumented, and which are not
    return trace

cdef int except_signal_id = 0
cdef object except_signal_name = os.getenv('PYTHON_AFL_SIGNAL') or '0'
if except_signal_name.isdigit():
    except_signal_id = int(except_signal_name)
else:
    if except_signal_name[:3] != 'SIG':
        except_signal_name = 'SIG' + except_signal_name
    except_signal_id = getattr(signal, except_signal_name)

cdef object excepthook
def excepthook(tp, value, traceback):
    os.kill(os.getpid(), except_signal_id)

cdef bint init_done = False

cdef int _init(bint persistent_mode) except -1:
    global afl_area, init_done
    use_forkserver = True
    try:
        os.write(FORKSRV_FD + 1, b'\0\0\0\0')
    except OSError as exc:
        if exc.errno == errno.EBADF:
            use_forkserver = False
        else:
            raise
    if init_done:
        raise RuntimeError('AFL already initialized')
    init_done = True
    child_stopped = False
    child_pid = 0
    while use_forkserver:
        [child_killed] = struct.unpack('I', os.read(FORKSRV_FD, 4))
        if child_stopped and child_killed:
            os.waitpid(child_pid, 0)
            child_stopped = False
        if child_stopped:
            os.kill(child_pid, signal.SIGCONT)
            child_stopped = False
        else:
            child_pid = os.fork()
            if not child_pid:
                # child:
                break
        # parent:
        os.write(FORKSRV_FD + 1, struct.pack('I', child_pid))
        (child_pid, status) = os.waitpid(child_pid, os.WUNTRACED if persistent_mode else 0)
        child_stopped = os.WIFSTOPPED(status)
        os.write(FORKSRV_FD + 1, struct.pack('I', status))
    if use_forkserver:
        os.close(FORKSRV_FD)
        os.close(FORKSRV_FD + 1)
    if except_signal_id != 0:
        sys.excepthook = excepthook
    cdef const char * afl_shm_id = getenv(SHM_ENV_VAR)
    if afl_shm_id == NULL:
        return 0
    afl_area = shmat(int(afl_shm_id), NULL, 0)
    if afl_area == <void*> -1:
        PyErr_SetFromErrno(OSError)
    sys.settrace(trace)
    return 0

def init():
    '''
    init()

    Start the fork server and enable instrumentation.

    This function should be called as late as possible, but before the input is
    read, and before any threads are started.
    '''
    _init(persistent_mode=False)

def start():
    '''
    deprecated alias for afl.init()
    '''
    warnings.warn('afl.start() is deprecated, use afl.init() instead', DeprecationWarning)
    _init(persistent_mode=False)

cdef bint persistent_allowed = False
cdef unsigned long persistent_counter = 0

def loop(max=None):
    '''
    while loop([max]):
        ...

    Start the fork server and enable instrumentation,
    then run the code inside the loop body in persistent mode.

    afl-fuzz >= 1.82b is required for this feature.
    '''
    global persistent_allowed, persistent_counter
    if persistent_counter == 0:
        persistent_allowed = os.getenv('PYTHON_AFL_PERSISTENT') is not None
        _init(persistent_mode=persistent_allowed)
        persistent_counter = 1
        return True
    cont = persistent_allowed and (
        max is None or
        persistent_counter < max
    )
    if cont:
        os.kill(os.getpid(), signal.SIGSTOP)
        persistent_counter += 1
        return True
    else:
        return False

__all__ = [
    'init',
    'loop',
]

# vim:ts=4 sts=4 sw=4 et
