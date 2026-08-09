=======
History
=======

0.3.0 (2026-08-09)
------------------

* **Breaking:** the CLI commands and the library API were renamed to share the same
  names. There are no aliases for the old names:

  * ``db create`` -> ``db create-db`` (``create_database`` -> ``create_db``)
  * ``db init-demo`` -> ``db create-demo-db`` (``init_demo_database`` -> ``create_demo_db``)
  * ``db create-readonly-user`` -> ``db create-user-readonly``
    (``create_readonly_user`` -> ``create_user_readonly``)
  * ``db next-names`` -> ``db show-next-db-name``
    (``next_database_names`` -> ``show_next_db_name``)

* **Breaking:** ``show-next-db-name`` prints only the next database name. The next user
  name is still available from ``PostgresMate.show_next_db_name()``.

0.2.0 (2026-08-09)
------------------

* Added a public API: ``PostgresMate``, ``PostgreSQLConfig`` and the module level
  convenience functions are importable from ``dbmate``.
* Backend operations raise ``DBMateException`` subclasses instead of returning ``bool``.
* SQL is built with ``psycopg2.sql``; passwords are bound parameters and no longer
  part of the statement text.
* ``--env-file`` is now honoured for the database settings.
* Added the ``db init-demo``, ``db create-readonly-user`` and ``db next-names`` commands
  (renamed in 0.3.0); commands exit ``1`` on failure and ``--dry-run`` is honoured.
* Added ``python -m dbmate``, ``py.typed`` and a test suite.
* **Breaking:** the old ``dbmate.postgresql.functions`` names were removed.

0.1.0 (2026-08-08)
------------------

* First release of the basic CLI on Github
