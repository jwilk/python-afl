This is experimental module that enables
`American fuzzy lop`_ instrumentation of Python code.

HOWTO
-----

* Add this code (ideally, after all other modules are already imported) to
  the target program::

      import afl
      afl.start()

* Disable hash randomization::

      $ export PYTHONHASHSEED=0

* Disable checks to detect instrumented binaries::

      $ export AFL_SKIP_CHECKS=1

* Run *afl-fuzz* as usual::

      $ afl-fuzz [options] -- /path/to/python/script

.. _American fuzzy lop: http://lcamtuf.coredump.cx/afl/

.. vim:ts=3 sts=3 sw=3 et
