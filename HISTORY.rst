=======
History
=======

0.7.0 (2026-08-10)
------------------

* **Breaking:** the ``database`` command group is renamed to ``postgresql``
  (hidden alias ``db`` -> ``pg``). The old names no longer work.
* Added ``dbsmate`` as a console-script alias for ``dbsetupmate``.

0.6.0 (2026-08-10)
------------------

* **Breaking:** ``db create-user-readonly`` -> ``db create-shared-user-readonly``
  (``create_user_readonly`` -> ``create_shared_user_readonly``). There is no alias.

* Added seven commands, each with a matching ``PostgresMate`` method and a module level
  function:

  * ``db show-dbs`` (``list_dbs``), ``db show-users`` (``list_users``), ``db show-config``
  * ``db set-user-password``, ``db revoke-shared-access``
  * ``db drop-db``, ``db drop-user``

* ``drop-db`` and ``drop-user`` ask for confirmation unless ``--yes`` is given.
* Added the ``ManagedDatabase`` model, returned by ``list_dbs``.

0.5.1 (2026-08-10)
------------------

* Internal refactor only; the public API and CLI are unchanged. ``manager.py``
  was split into a ``BasePostgresMate`` parent (the internals) and
  ``PostgresMate`` (the public API), SQL construction moved to
  ``dbsetupmate.postgresql.statements``, and the ``translate_error`` /
  ``render_statement`` / ``require_password`` helpers moved to
  ``dbsetupmate.postgresql.helpers``.

0.5.0 (2026-08-10)
------------------

* **Breaking:** ``create_db`` no longer grants shared access. Granting is now a
  separate step:

  * CLI: new ``db grant-shared-access --user-name ...``; ``create-db`` dropped
    ``--skip-shared-access``.
  * API: new ``PostgresMate.grant_shared_access`` / ``grant_shared_access``;
    ``create_db(grant_shared_access=...)`` removed, as was
    ``CreatedDatabase.granted_shared_access``.

0.4.1 (2026-08-09)
------------------

* ``task py:pytest-integration`` now runs the integration suite against every
  PostgreSQL version (``database-15`` .. ``database-18``) on port ``5432`` and fails
  if any version fails, instead of only reaching one server on port ``5415``.

0.4.0 (2026-08-09)
------------------

* **Breaking:** the "demo" database is now the **shared** database - a database other users
  of the server read from, not a throwaway teaching one. Everything named after it was
  renamed. There are no aliases and no environment fallbacks for the old names:

  * environment: ``POSTGRESQL_DEMO_*`` -> ``POSTGRESQL_SHARED_*`` (``_DB``, ``_USER``,
    ``_PASSWORD``, ``_USER_READONLY``, ``_USER_READONLY_PASSWORD``)
  * CLI: ``db create-demo-db`` -> ``db create-shared-db``;
    ``create-db --skip-demo-access`` -> ``--skip-shared-access``
  * API: ``create_demo_db`` -> ``create_shared_db``,
    ``PostgresMate.harden_demo_schema`` -> ``harden_shared_schema``,
    ``create_db(grant_demo_access=...)`` -> ``grant_shared_access``,
    ``CreatedDatabase.granted_demo_access`` -> ``granted_shared_access``
  * ``PostgreSQLConfig`` fields: ``demo_db``, ``demo_user``, ``demo_password``,
    ``demo_user_readonly``, ``demo_user_readonly_password`` -> ``shared_*``

* **Breaking:** the default identifiers changed with them: ``dbsetupmate_db_demo`` ->
  ``dbsetupmate_db_shared``, ``dbsetupmate_user_demo`` -> ``dbsetupmate_user_shared``,
  ``dbsetupmate_user_demo_ro`` -> ``dbsetupmate_user_shared_ro``.


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
  convenience functions are importable from ``dbsetupmate``.
* Backend operations raise ``DBSetupMateException`` subclasses instead of returning ``bool``.
* SQL is built with ``psycopg2.sql``; passwords are bound parameters and no longer
  part of the statement text.
* ``--env-file`` is now honoured for the database settings.
* Added the ``db init-demo``, ``db create-readonly-user`` and ``db next-names`` commands
  (renamed in 0.3.0); commands exit ``1`` on failure and ``--dry-run`` is honoured.
* Added ``python -m dbsetupmate``, ``py.typed`` and a test suite.
* **Breaking:** the old ``dbsetupmate.postgresql.functions`` names were removed.

0.1.0 (2026-08-08)
------------------

* First release of the basic CLI on Github
