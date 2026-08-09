=======
History
=======

0.2.0 (2026-08-09)
------------------

* Added a public API: ``PostgresMate``, ``PostgreSQLConfig`` and the module level
  convenience functions are importable from ``dbmate``.
* Backend operations raise ``DBMateException`` subclasses instead of returning ``bool``.
* SQL is built with ``psycopg2.sql``; passwords are bound parameters and no longer
  part of the statement text.
* ``--env-file`` is now honoured for the database settings.
* Added the ``db init-demo``, ``db create-readonly-user`` and ``db next-names`` commands;
  commands exit ``1`` on failure and ``--dry-run`` is honoured.
* Added ``python -m dbmate``, ``py.typed`` and a test suite.
* **Breaking:** the old ``dbmate.postgresql.functions`` names were removed.

0.1.0 (2026-08-08)
------------------

* First release of the basic CLI on Github
