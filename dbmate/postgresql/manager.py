"""The PostgreSQL backend of dbmate.

All real database work lives here. :class:`PostgresMate` is the entry point for
library consumers; its ``_``-prefixed internals sit on the :class:`BasePostgresMate`
parent class it inherits from. The SQL those methods run is assembled in
:mod:`dbmate.postgresql.statements`, and :mod:`dbmate.postgresql.functions` wraps
the public API in module level convenience functions.
"""

from typing import Iterable, List, Optional, Sequence

from dbmate.configs import cprint, logger
from dbmate.exceptions import (
    DatabaseAlreadyExistsException,
    DBMateException,
    DBUserAlreadyExistsException,
)
from dbmate.postgresql import statements
from dbmate.postgresql.configs import PostgreSQLConfig
from dbmate.postgresql.connection import connect
from dbmate.postgresql.helpers import render_statement, require_password
from dbmate.postgresql.identifiers import normalize_identifier
from dbmate.postgresql.models import CreatedDatabase, DatabaseNames
from dbmate.postgresql.statements import Statement


class BasePostgresMate:  # pylint: disable=too-few-public-methods
    """Connection, execution and inspection internals shared by :class:`PostgresMate`.

    This holds everything the public API is built on - opening connections,
    running or announcing statements, and the low-level existence checks - so
    that :class:`PostgresMate` reads as a list of the operations dbmate offers.

    Args:
        config (PostgreSQLConfig, optional): connection settings. Defaults to
            :meth:`PostgreSQLConfig.from_env`, read at construction time.
        dry_run (bool): when ``True``, read-only queries still run but no
            statement that changes the server is executed.
    """

    def __init__(self, config: Optional[PostgreSQLConfig] = None, *, dry_run: bool = False) -> None:
        self.config = config if config is not None else PostgreSQLConfig.from_env()
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # connections
    # ------------------------------------------------------------------

    def _admin_connection(self, database: Optional[str] = None, autocommit: bool = True):
        """Opens a connection as the administrative role."""

        return connect(
            self.config,
            database=database or self.config.database,
            user=self.config.admin_user,
            password=self.config.admin_password,
            autocommit=autocommit,
        )

    def _connection(self, database: str, user: str, password: str, autocommit: bool = True):
        """Opens a connection as an arbitrary role."""

        return connect(self.config, database=database, user=user, password=password, autocommit=autocommit)

    # ------------------------------------------------------------------
    # inspection
    # ------------------------------------------------------------------

    def _preflight(self, db_name: str, db_user: str) -> None:
        """Fails early on the two common collisions, before anything is created."""

        with self._admin_connection() as cursor:
            if self._database_exists(cursor, db_name):
                raise DatabaseAlreadyExistsException(f"Database '{db_name}' already exists")
            for role in (db_name, db_user):
                if self._role_exists(cursor, role):
                    raise DBUserAlreadyExistsException(f"Role '{role}' already exists")

    @staticmethod
    def _database_exists(cursor, name: str) -> bool:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (name,))
        return cursor.fetchone() is not None

    @staticmethod
    def _role_exists(cursor, name: str) -> bool:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", (name,))
        return cursor.fetchone() is not None

    # ------------------------------------------------------------------
    # shared read-only access, cleanup
    # ------------------------------------------------------------------

    def _grant_shared_readonly(self, role: str) -> None:
        """Grants SELECT on the shared schema. Only its owner may do this."""

        with self._connection(self.config.shared_db, self.config.shared_user, self.config.shared_password) as cursor:
            self._execute_all(cursor, statements.shared_readonly_statements(role))

    def _drop_roles_quietly(self, roles: Sequence[str]) -> None:
        """Best effort cleanup of roles this call created; never masks the original error."""

        try:
            with self._admin_connection() as cursor:
                for role in roles:
                    cursor.execute(statements.drop_role_statement(role))
            logger.info("Rolled back the roles %s after a failed database creation", ", ".join(roles))
        except DBMateException as ex:
            logger.warning("Could not roll back the roles %s: %s", ", ".join(roles), ex)

    # ------------------------------------------------------------------
    # execution
    # ------------------------------------------------------------------

    def _execute_all(self, cursor, statement_list: Iterable[Statement]) -> None:
        if self.dry_run:
            self._announce(statement_list, cursor)
            return
        for statement, params in statement_list:
            logger.debug("Executing: %s", render_statement(statement, cursor))
            cursor.execute(statement, params)

    @staticmethod
    def _announce(statement_list: Iterable[Statement], cursor=None) -> None:
        """Reports statements that a dry run is skipping."""

        for statement, _ in statement_list:
            # No square brackets: Rich would read them as markup. No wrapping either,
            # so a statement stays on one line and can be copied out as-is.
            cprint(f"dry-run: {render_statement(statement, cursor)}", style="yellow", soft_wrap=True, log_level="info")


class PostgresMate(BasePostgresMate):
    """Creates and maintains PostgreSQL databases, roles and grants.

    Every method raises a :class:`~dbmate.exceptions.DBMateException` subclass on
    failure instead of reporting it through a return value.

    Args:
        config (PostgreSQLConfig, optional): connection settings. Defaults to
            :meth:`PostgreSQLConfig.from_env`, read at construction time.
        dry_run (bool): when ``True``, read-only queries still run but no
            statement that changes the server is executed.

    Example:
        >>> mate = PostgresMate()
        >>> mate.create_db("course_db_01", "course_user_01", "s3cret")
    """

    # ------------------------------------------------------------------
    # inspection
    # ------------------------------------------------------------------

    def database_exists(self, name: str) -> bool:
        """Reports whether a database exists.

        Args:
            name (str): database name

        Returns:
            bool: ``True`` if the database is present
        """

        name = normalize_identifier(name, "database")
        with self._admin_connection() as cursor:
            return self._database_exists(cursor, name)

    def user_exists(self, name: str) -> bool:
        """Reports whether a role exists.

        Args:
            name (str): role name

        Returns:
            bool: ``True`` if the role is present
        """

        name = normalize_identifier(name, "role")
        with self._admin_connection() as cursor:
            return self._role_exists(cursor, name)

    def show_next_db_name(self) -> DatabaseNames:
        """Derives the next free auto-generated database and user names.

        Looks at every database whose name starts with the configured prefix and
        continues after the highest number already in use, so that deleting a
        database out of order does not produce a collision.

        Returns:
            DatabaseNames: the next free names and the number they are built from
        """

        prefix = f"{self.config.db_prefix}_"
        with self._admin_connection() as cursor:
            cursor.execute(
                "SELECT datname FROM pg_database WHERE left(datname::text, %(length)s) = %(prefix)s;",
                {"length": len(prefix), "prefix": prefix},
            )
            rows = cursor.fetchall()

        orders = [int(suffix) for suffix in (str(row[0])[len(prefix) :] for row in rows) if suffix.isdigit()]
        order = max(orders, default=0) + 1

        return DatabaseNames(
            database=f"{self.config.db_prefix}_{order:02d}",
            user=f"{self.config.user_prefix}_{order:02d}",
            order=order,
        )

    # ------------------------------------------------------------------
    # provisioning
    # ------------------------------------------------------------------

    def create_db(
        self,
        db_name: str,
        db_user: str,
        db_password: str,
    ) -> CreatedDatabase:
        """Creates a database, its owning group role and a login role for it.

        Args:
            db_name (str): name of the new database, also used for the owning group role
            db_user (str): name of the login role that owns the database
            db_password (str): password for the login role

        Returns:
            CreatedDatabase: what was created

        Raises:
            InvalidIdentifierException: if a name is not a usable identifier
            DatabaseAlreadyExistsException: if the database is already present
            DBUserAlreadyExistsException: if one of the roles is already present
            DBMateException: for any other failure

        Note:
            On failure after the database itself was created, the objects created
            up to that point are left in place - only the roles are rolled back,
            and only when ``CREATE DATABASE`` is what failed. dbmate never drops a
            database implicitly.
        """

        db_name = normalize_identifier(db_name, "database")
        db_user = normalize_identifier(db_user, "role")
        require_password(db_password, db_user)

        self._preflight(db_name, db_user)

        role_statements = statements.owner_and_login_role_statements(db_name, db_user, db_password)
        database_statements = statements.create_database_statements(db_name, db_user)
        owner_grant = statements.owner_grant_all_on_public_schema(db_user)
        schema_statements = statements.public_schema_create_statements(db_name, db_user)

        if self.dry_run:
            planned: List[Statement] = [*role_statements, *database_statements, owner_grant, *schema_statements]
            # Borrow a cursor purely so the statements render as readable SQL.
            with self._admin_connection() as cursor:
                self._announce(planned, cursor)
            return CreatedDatabase(
                database=db_name,
                owner_role=db_name,
                login_role=db_user,
                dry_run=True,
            )

        # CREATE ROLE and GRANT are transactional, so the two roles are created
        # all-or-nothing and need no compensating logic of their own.
        with self._admin_connection(autocommit=False) as cursor:
            self._execute_all(cursor, role_statements)
        logger.info("Roles '%s' and '%s' were created", db_name, db_user)

        # CREATE DATABASE cannot run inside a transaction, hence a second,
        # autocommitting connection - and hence the manual cleanup below.
        try:
            with self._admin_connection() as cursor:
                self._execute_all(cursor, database_statements)
        except DBMateException:
            self._drop_roles_quietly([db_user, db_name])
            raise
        logger.info("Database '%s' was created", db_name)

        # The owner has to hand out rights on its own public schema itself.
        with self._connection(db_name, db_user, db_password) as cursor:
            self._execute_all(cursor, [owner_grant])
        self.grant_public_schema_rights(db_name, db_user)

        return CreatedDatabase(
            database=db_name,
            owner_role=db_name,
            login_role=db_user,
        )

    def grant_public_schema_rights(self, db_name: str, db_user: str) -> None:
        """Grants CREATE on the public schema of a database to its two roles.

        Args:
            db_name (str): the database, and the name of its owning group role
            db_user (str): the login role
        """

        db_name = normalize_identifier(db_name, "database")
        db_user = normalize_identifier(db_user, "role")

        with self._admin_connection(database=db_name) as cursor:
            self._execute_all(cursor, statements.public_schema_create_statements(db_name, db_user))

    def grant_shared_access(self, role: str) -> None:
        """Grants a role read-only access to the shared database.

        Opens the shared database to the role (GRANT CONNECT, as admin), then
        grants SELECT on its public schema (as the shared owner - only it may).

        Args:
            role (str): the role to grant read-only shared access to
        """

        role = normalize_identifier(role, "role")

        with self._admin_connection() as cursor:
            self._execute_all(cursor, [statements.grant_connect_statement(self.config.shared_db, role)])

        self._grant_shared_readonly(role)

    def create_user_readonly(self, user_name: Optional[str] = None, password: Optional[str] = None) -> str:
        """Creates a role with read-only access to the shared database.

        Args:
            user_name (str, optional): role to create. Defaults to the configured
                ``POSTGRESQL_SHARED_USER_READONLY``.
            password (str, optional): its password. Defaults to the configured
                ``POSTGRESQL_SHARED_USER_READONLY_PASSWORD``.

        Returns:
            str: the normalised role name

        Raises:
            DBUserAlreadyExistsException: if the role is already present
            DBMateException: for any other failure
        """

        user_name = normalize_identifier(user_name or self.config.shared_user_readonly, "role")
        password = password if password is not None else self.config.shared_user_readonly_password
        require_password(password, user_name)

        with self._admin_connection() as cursor:
            self._execute_all(cursor, [statements.login_role_statement(user_name, password)])

        self.grant_shared_access(user_name)
        logger.info("Read-only role '%s' was created", user_name)

        return user_name

    def harden_shared_schema(self) -> None:
        """Stops everyone but the shared owner from creating objects in the shared schema."""

        with self._admin_connection(database=self.config.shared_db) as cursor:
            self._execute_all(cursor, statements.harden_shared_schema_statements(self.config.shared_user))

    def create_shared_db(self) -> CreatedDatabase:
        """Creates the shared database and its owner, then hardens its schema.

        This never grants shared access to the new owner: :meth:`create_db` no
        longer does that, and :meth:`grant_shared_access` is deliberately not
        called here - it would try to grant the shared database to itself.

        Returns:
            CreatedDatabase: what was created
        """

        created = self.create_db(
            db_name=self.config.shared_db,
            db_user=self.config.shared_user,
            db_password=self.config.shared_password,
        )
        self.harden_shared_schema()
        logger.info("Shared database '%s' was initialised", self.config.shared_db)

        return created
