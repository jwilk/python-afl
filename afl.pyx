# Copyright © 2014-2015 Jakub Wilk <jwilk@jwilk.net>
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

'''
American fuzzy lop fork server and instrumentation for pure-Python code
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

cdef bint persistent_mode = os.getenv('AFL_PERSISTENT')

def start():
    '''
    start()

    Start the fork server and enable instrumentation.

    This function should be called as late as possible, but before the input is
    read, and before any threads are started.
    '''
    cdef int use_forkserver = 1
    global afl_area
    try:
        os.write(FORKSRV_FD + 1, b'\0\0\0\0')
    except OSError as exc:
        if exc.errno == errno.EBADF:
            use_forkserver = 0
        else:
            raise
    child_stopped = False
    while use_forkserver:
        [child_killed] = struct.unpack('I', os.read(FORKSRV_FD, 4))
        if child_stopped and child_killed:
            if child_killed:
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
    afl_shm_id = os.getenv(SHM_ENV_VAR)
    if afl_shm_id is None:
        return
    afl_shm_id = int(afl_shm_id)
    afl_area = shmat(afl_shm_id, NULL, 0)
    if afl_area == <void*> -1:
        PyErr_SetFromErrno(OSError)
    sys.settrace(trace)

cdef unsigned long persistent_counter = 0

def persistent(max=None):
    '''
    while persistent([max]):
        ...

    Run the code inside the loop body in persistent mode.
    '''
    global persistent_counter
    if not persistent_mode:
        max = 1
    elif persistent_counter > 0:
        os.kill(os.getpid(), signal.SIGSTOP)
    try:
        return (
            max is None or
            persistent_counter < max
        )
    finally:
        persistent_counter += 1

__all__ = ['start', 'persistent']

# vim:ts=4 sts=4 sw=4 et
