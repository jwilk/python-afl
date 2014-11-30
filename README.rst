This is experimental module that enables
`American fuzzy lop`_ instrumentation of Python code.

HOWTO
-----

* Add this code (ideally, after all other modules are already imported) to
  the target program::

      import afl
      afl.start()

* Use *py-afl-fuzz* instead of *afl-fuzz*::

      $ py-afl-fuzz [options] -- /path/to/fuzzed/python/script [...]

.. _American fuzzy lop: http://lcamtuf.coredump.cx/afl/

.. vim:ts=3 sts=3 sw=3 et
