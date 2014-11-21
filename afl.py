'''
American fuzzy lop instrumentation for Python
'''

import os
import signal
import struct
import sys
import warnings

import sysv_ipc

# These constants must be kept in sync with afl-fuzz:
SHM_ENV_VAR = '__AFL_SHM_ID'
EXEC_FAIL = 0x55
FORKSRV_FD = 198
MAP_SIZE_POW2 = 14
MAP_SIZE = 1 << MAP_SIZE_POW2

class AflError(Exception):
    pass

def trace(frame, event, arg):
    global prev_location
    path = frame.f_code.co_filename
    location = hash((path, frame.f_lineno)) % MAP_SIZE
    offset = location ^ prev_location
    b = afl_area.read(1, offset)
    b = bytes([(ord(b) + 1) & 0xFF])
    afl_area.write(b, offset)
    prev_location = location
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
    afl_area = sysv_ipc.attach(afl_shm_id)
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
    global prev_location
    prev_location = 0
    sys.excepthook = excepthook
    sys.settrace(trace)

__all__ = ['start']

# vim:ts=4 sts=4 sw=4 et
