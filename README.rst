This is experimental module that enables
`American fuzzy lop`_ fork server and instrumentation for Python code.

.. _American fuzzy lop: http://lcamtuf.coredump.cx/afl/

HOWTO
-----

* Add this code (ideally, after all other modules are already imported) to
  the target program::

      import afl
      afl.start()

* Use *py-afl-fuzz* instead of *afl-fuzz*::

      $ py-afl-fuzz [options] -- /path/to/fuzzed/python/script [...]

Environment variables
---------------------

The following environment variables affect *python-afl* behavior:

``PYTHON_AFL_SIGNAL``

   By default, *python-afl* installs an exception hook
   that kills the current process with ``SIGUSR1``.
   That way *afl-fuzz* can treat unhandled exceptions as crashes.
   You can set ``PYTHON_AFL_SIGNAL`` to another signal;
   or set it to ``0`` to disable the exception hook.

``PYTHON_AFL_DUMB``

   You can set ``PYTHON_AFL_DUMB`` to a non-empty string
   to disable instrumentation.

.. vim:ts=3 sts=3 sw=3 et
