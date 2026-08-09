"""The PostgreSQL backend of dbmate.

All real database work lives here. :class:`PostgresMate` is the entry point for
library consumers; :mod:`dbmate.postgresql.functions` wraps it in module level
convenience functions.
"""

from typing import Iterable, List, Optional, Sequence, Tuple

from psycopg2 import sql

from dbmate.configs import cprint, logger
from dbmate.exceptions import (
    DatabaseAlreadyExistsException,
    DBMateException,
    DBUserAlreadyExistsException,
)
from dbmate.postgresql.configs import PostgreSQLConfig
from dbmate.postgresql.connection import connect
from dbmate.postgresql.identifiers import normalize_identifier
from dbmate.postgresql.models import CreatedDatabase, DatabaseNames

#: A statement together with its bound parameters.
Statement = Tuple[sql.Composable, Optional[tuple]]

#: The PUBLIC pseudo-role. It is a keyword, not an identifier: quoting it would
#: make PostgreSQL look for a role literally named "public" and fail with 42704.
PUBLIC_ROLE = sql.SQL("PUBLIC")

#: The schema name `public` *is* an ordinary identifier.
PUBLIC_SCHEMA = sql.Identifier("public")

_ROLE_ATTRIBUTES = "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"


class PostgresMate:
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

    def __init__(self, config: Optional[PostgreSQLConfig] = None, *, dry_run: bool = False) -> None:
        self.config = config if config is not None else PostgreSQLConfig.from_env()
        self.dry_run = dry_run

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
        *,
        grant_demo_access: bool = True,
    ) -> CreatedDatabase:
        """Creates a database, its owning group role and a login role for it.

        Args:
            db_name (str): name of the new database, also used for the owning group role
            db_user (str): name of the login role that owns the database
            db_password (str): password for the login role
            grant_demo_access (bool): also grant the new role read-only access to
                the shared demo database

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
        _require_password(db_password, db_user)

        self._preflight(db_name, db_user)

        role_statements: List[Statement] = [
            (
                sql.SQL("CREATE ROLE {role} " + _ROLE_ATTRIBUTES + " NOLOGIN").format(role=sql.Identifier(db_name)),
                None,
            ),
            (
                # The password is a bound parameter, so it never becomes part of the
                # statement text and cannot leak through logs or a traceback.
                # psycopg2 interpolates client side, which is why this works in DDL
                # (psycopg3 and asyncpg bind server side and would reject it).
                sql.SQL("CREATE ROLE {role} " + _ROLE_ATTRIBUTES + " LOGIN ENCRYPTED PASSWORD %s").format(
                    role=sql.Identifier(db_user)
                ),
                (db_password,),
            ),
            (
                sql.SQL("GRANT {group} TO {member}").format(
                    group=sql.Identifier(db_name), member=sql.Identifier(db_user)
                ),
                None,
            ),
        ]

        database_statements: List[Statement] = [
            (
                sql.SQL("CREATE DATABASE {database} WITH OWNER = {owner}").format(
                    database=sql.Identifier(db_name), owner=sql.Identifier(db_user)
                ),
                None,
            ),
            (
                sql.SQL("REVOKE ALL ON DATABASE {database} FROM {public}").format(
                    database=sql.Identifier(db_name), public=PUBLIC_ROLE
                ),
                None,
            ),
        ]
        if grant_demo_access:
            database_statements.append(
                (
                    sql.SQL("GRANT CONNECT ON DATABASE {demo} TO {role}").format(
                        demo=sql.Identifier(self.config.demo_db), role=sql.Identifier(db_user)
                    ),
                    None,
                )
            )

        if self.dry_run:
            planned = list(role_statements)
            planned += database_statements
            planned += [
                (
                    sql.SQL("GRANT ALL ON SCHEMA {schema} TO {role} WITH GRANT OPTION").format(
                        schema=PUBLIC_SCHEMA, role=sql.Identifier(db_user)
                    ),
                    None,
                )
            ]
            planned += self._public_schema_statements(db_name, db_user)
            if grant_demo_access:
                planned += self._demo_readonly_statements(db_user)
            # Borrow a cursor purely so the statements render as readable SQL.
            with self._admin_connection() as cursor:
                self._announce(planned, cursor)
            return CreatedDatabase(
                database=db_name,
                owner_role=db_name,
                login_role=db_user,
                granted_demo_access=False,
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
            self._execute_all(
                cursor,
                [
                    (
                        sql.SQL("GRANT ALL ON SCHEMA {schema} TO {role} WITH GRANT OPTION").format(
                            schema=PUBLIC_SCHEMA, role=sql.Identifier(db_user)
                        ),
                        None,
                    )
                ],
            )
        self.grant_public_schema_rights(db_name, db_user)

        if grant_demo_access:
            self._grant_demo_readonly(db_user)

        return CreatedDatabase(
            database=db_name,
            owner_role=db_name,
            login_role=db_user,
            granted_demo_access=grant_demo_access,
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
            self._execute_all(cursor, self._public_schema_statements(db_name, db_user))

    def create_user_readonly(self, user_name: Optional[str] = None, password: Optional[str] = None) -> str:
        """Creates a role with read-only access to the shared demo database.

        Args:
            user_name (str, optional): role to create. Defaults to the configured
                ``POSTGRESQL_DEMO_USER_READONLY``.
            password (str, optional): its password. Defaults to the configured
                ``POSTGRESQL_DEMO_USER_READONLY_PASSWORD``.

        Returns:
            str: the normalised role name

        Raises:
            DBUserAlreadyExistsException: if the role is already present
            DBMateException: for any other failure
        """

        user_name = normalize_identifier(user_name or self.config.demo_user_readonly, "role")
        password = password if password is not None else self.config.demo_user_readonly_password
        _require_password(password, user_name)

        statements: List[Statement] = [
            (
                sql.SQL("CREATE ROLE {role} " + _ROLE_ATTRIBUTES + " LOGIN ENCRYPTED PASSWORD %s").format(
                    role=sql.Identifier(user_name)
                ),
                (password,),
            ),
            (
                sql.SQL("GRANT CONNECT ON DATABASE {demo} TO {role}").format(
                    demo=sql.Identifier(self.config.demo_db), role=sql.Identifier(user_name)
                ),
                None,
            ),
        ]

        with self._admin_connection() as cursor:
            self._execute_all(cursor, statements)

        self._grant_demo_readonly(user_name)
        logger.info("Read-only role '%s' was created", user_name)

        return user_name

    def harden_demo_schema(self) -> None:
        """Stops everyone but the demo owner from creating objects in the demo schema."""

        statements: List[Statement] = [
            (
                sql.SQL("REVOKE CREATE ON SCHEMA {schema} FROM {public}").format(
                    schema=PUBLIC_SCHEMA, public=PUBLIC_ROLE
                ),
                None,
            ),
            (
                sql.SQL("GRANT CREATE ON SCHEMA {schema} TO {role}").format(
                    schema=PUBLIC_SCHEMA, role=sql.Identifier(self.config.demo_user)
                ),
                None,
            ),
        ]

        with self._admin_connection(database=self.config.demo_db) as cursor:
            self._execute_all(cursor, statements)

    def create_demo_db(self) -> CreatedDatabase:
        """Creates the shared demo database and its owner, then hardens its schema.

        Bootstrapping the demo database is deliberately not routed through
        :meth:`create_db` with the demo grants enabled - that would try to
        grant the demo database to itself while creating it.

        Returns:
            CreatedDatabase: what was created
        """

        created = self.create_db(
            db_name=self.config.demo_db,
            db_user=self.config.demo_user,
            db_password=self.config.demo_password,
            grant_demo_access=False,
        )
        self.harden_demo_schema()
        logger.info("Demo database '%s' was initialised", self.config.demo_db)

        return created

    # ------------------------------------------------------------------
    # internals
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

    def _public_schema_statements(self, db_name: str, db_user: str) -> List[Statement]:
        return [
            (
                sql.SQL("GRANT CREATE ON SCHEMA {schema} TO {role}").format(
                    schema=PUBLIC_SCHEMA, role=sql.Identifier(role)
                ),
                None,
            )
            for role in (db_name, db_user)
        ]

    @staticmethod
    def _demo_readonly_statements(role: str) -> List[Statement]:
        return [
            (
                sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {role}").format(
                    schema=PUBLIC_SCHEMA, role=sql.Identifier(role)
                ),
                None,
            ),
            (
                sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT SELECT ON TABLES TO {role}").format(
                    schema=PUBLIC_SCHEMA, role=sql.Identifier(role)
                ),
                None,
            ),
        ]

    def _grant_demo_readonly(self, role: str) -> None:
        """Grants SELECT on the demo schema. Only its owner may do this."""

        with self._connection(self.config.demo_db, self.config.demo_user, self.config.demo_password) as cursor:
            self._execute_all(cursor, self._demo_readonly_statements(role))

    def _drop_roles_quietly(self, roles: Sequence[str]) -> None:
        """Best effort cleanup of roles this call created; never masks the original error."""

        try:
            with self._admin_connection() as cursor:
                for role in roles:
                    cursor.execute(sql.SQL("DROP ROLE IF EXISTS {role}").format(role=sql.Identifier(role)))
            logger.info("Rolled back the roles %s after a failed database creation", ", ".join(roles))
        except DBMateException as ex:
            logger.warning("Could not roll back the roles %s: %s", ", ".join(roles), ex)

    def _execute_all(self, cursor, statements: Iterable[Statement]) -> None:
        if self.dry_run:
            self._announce(statements, cursor)
            return
        for statement, params in statements:
            logger.debug("Executing: %s", _render(statement, cursor))
            cursor.execute(statement, params)

    @staticmethod
    def _announce(statements: Iterable[Statement], cursor=None) -> None:
        """Reports statements that a dry run is skipping."""

        for statement, _ in statements:
            # No square brackets: Rich would read them as markup. No wrapping either,
            # so a statement stays on one line and can be copied out as-is.
            cprint(f"dry-run: {_render(statement, cursor)}", style="yellow", soft_wrap=True, log_level="info")


def _render(statement: sql.Composable, cursor) -> str:
    """Renders a statement for display.

    Bound parameters stay as ``%s``, so a password is never rendered.

    Args:
        statement (sql.Composable): the statement to render
        cursor: a live cursor, or ``None`` when there is none at hand

    Returns:
        str: the SQL text, or its repr if it cannot be rendered without a connection
    """

    if cursor is None:
        return repr(statement)
    try:
        return statement.as_string(cursor)
    except (TypeError, AttributeError):  # pragma: no cover - needs a live connection
        return repr(statement)


def _require_password(password: Optional[str], role: str) -> None:
    """Rejects an empty password before it reaches the server."""

    if not password:
        raise DBMateException(f"A password is required for the role '{role}'")
