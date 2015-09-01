This is experimental module that enables
`American fuzzy lop`_ fork server and instrumentation for pure-Python code.

.. _American fuzzy lop: http://lcamtuf.coredump.cx/afl/

HOWTO
-----

* Add this code (ideally, after all other modules are already imported) to
  the target program:

  .. code:: python

      import afl
      afl.init()

* Optionally, add this code at the end of the target program:

  .. code:: python

      os._exit(0)

  This should speed up fuzzing considerably,
  at the risk of not catching bugs that could happen during normal exit.

* For persistent mode, wrap the tested code in this loop:

  .. code:: python

      while afl.loop(N):
         ...

  where ``N`` is the number of inputs to process before restarting.

  You shouldn't call ``afl.init()`` in this case.

  afl-fuzz ≥ 1.82b is required for this feature.

* Use *py-afl-fuzz* instead of *afl-fuzz*::

      $ py-afl-fuzz [options] -- /path/to/fuzzed/python/script [...]

* The instrumentation is a bit slow at the moment,
  so you might want to enable the dumb mode (``-n``),
  while still leveraging the fork server.

Environment variables
---------------------

The following environment variables affect *python-afl* behavior:

``PYTHON_AFL_SIGNAL``

   If this variable is set, *python-afl* installs an exception hook
   that kills the current process with the selected signal.
   That way *afl-fuzz* can treat unhandled exceptions as crashes.

   By default, *py-afl-fuzz* set this variable to ``SIGUSR1``.

   You can set ``PYTHON_AFL_SIGNAL`` to another signal;
   or set it to ``0`` to disable the exception hook.

``PYTHON_AFL_PERSISTENT``

   Persistent mode is enabled only if this variable is set.

   *py-afl-fuzz* sets this variable automatically,
   so there should normally no need to set it manually.

.. vim:ts=3 sts=3 sw=3 et
