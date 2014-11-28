This is experimental module that enables
`American fuzzy lop`_ instrumentation of Python code.

HOWTO
-----

* Add this code (ideally, after all other modules are already imported) to
  the target program::

      import afl
      afl.start()

* Disable has randomization::

      $ export PYTHONHASHSEED=0

* *afl-fuzz* doesn't like fuzzing scripts, so you have to use::

      $ afl-fuzz [options] -- python /path/to/script

  instead of::

      $ afl-fuzz [options] -- /path/to/script

.. _American fuzzy lop: http://lcamtuf.coredump.cx/afl/

.. vim:ts=3 sts=3 sw=3 et
