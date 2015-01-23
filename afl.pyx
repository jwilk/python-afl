# encoding=UTF-8

# Copyright © 2014 Jakub Wilk <jwilk@jwilk.net>
#
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
DEF MAP_SIZE_POW2 = 15
DEF MAP_SIZE = 1 << MAP_SIZE_POW2

cdef extern from 'sys/shm.h':
    unsigned char *shmat(int shmid, void *shmaddr, int shmflg)

cdef unsigned char *afl_area = NULL
cdef unsigned long prev_location = 0

class AflError(Exception):
    pass

def trace(frame, event, arg):
    global prev_location
    cdef unsigned long location, offset
    path = frame.f_code.co_filename
    location = hash((path, frame.f_lineno))
    location %= MAP_SIZE
    offset = location ^ prev_location
    prev_location = location
    afl_area[offset] += 1
    if event == 'call' and (path.startswith('<') or path.startswith('/usr/lib/python')):
        # Skip globally-installed Python modules.
        # Instrumenting everything would make fuzzing awfully slow.
        # TODO: Make it configurable which modules are instrumented, and which are not.
        return
    return trace

def excepthook(tp, value, traceback):
    # TODO: Make the signal configurable.
    os.kill(os.getpid(), signal.SIGUSR1)

def start():
    global afl_area
    afl_shm_id = os.getenv(SHM_ENV_VAR)
    if afl_shm_id is None:
        warnings.warn('no AFL environment')
        return
    if os.getenv('PYTHONHASHSEED', '') != '0':
        raise RuntimeError('PYTHONHASHSEED != 0')
    afl_shm_id = int(afl_shm_id)
    afl_area = shmat(afl_shm_id, NULL, 0)
    os.write(FORKSRV_FD + 1, b'\0\0\0\0')
    while 1:
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
    os.close(FORKSRV_FD)
    os.close(FORKSRV_FD + 1)
    sys.excepthook = excepthook
    if not os.getenv('PYTHON_AFL_DUMB'):
        sys.settrace(trace)

__all__ = ['start']

# vim:ts=4 sts=4 sw=4 et
