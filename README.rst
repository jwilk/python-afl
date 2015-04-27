This is experimental module that enables
`American fuzzy lop`_ fork server and instrumentation for pure-Python code.

.. _American fuzzy lop: http://lcamtuf.coredump.cx/afl/

HOWTO
-----

* Add this code (ideally, after all other modules are already imported) to
  the target program::

      import afl
      afl.start()

* Optionally, add this code at the end of the target program::

      os._exit(0)

  This should speed up fuzzing considerably,
  at the risk of not catching bugs that could happen during normal exit.

* Use *py-afl-fuzz* instead of *afl-fuzz*::

      $ py-afl-fuzz [options] -- /path/to/fuzzed/python/script [...]

* The instrumentation is a bit slow at the moment,
  so you might want to enable the dumb mode (``-n``),
  while still leveraging the fork server.

Environment variables
---------------------

The following environment variables affect *python-afl* behavior:

``PYTHON_AFL_SIGNAL``

   By default, *python-afl* installs an exception hook
   that kills the current process with ``SIGUSR1``.
   That way *afl-fuzz* can treat unhandled exceptions as crashes.
   You can set ``PYTHON_AFL_SIGNAL`` to another signal;
   or set it to ``0`` to disable the exception hook.

.. vim:ts=3 sts=3 sw=3 et
