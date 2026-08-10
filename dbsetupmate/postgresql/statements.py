"""SQL statement builders for the PostgreSQL backend.

Every statement dbsetupmate sends is assembled here, so :mod:`dbsetupmate.postgresql.manager`
stays pure orchestration and the SQL can be read (and tested) in one place.

Each builder returns either a single :data:`Statement` or a ``List[Statement]``:
a statement is a :class:`psycopg2.sql.Composable` paired with its bound
parameters (``None`` when there are none). Identifiers are quoted with
``sql.Identifier``; a password is always a bound ``%s`` parameter so it never
becomes part of the statement text.
"""

from typing import List, Optional, Tuple

from psycopg2 import sql

#: A statement together with its bound parameters.
Statement = Tuple[sql.Composable, Optional[tuple]]

#: The PUBLIC pseudo-role. It is a keyword, not an identifier: quoting it would
#: make PostgreSQL look for a role literally named "public" and fail with 42704.
PUBLIC_ROLE = sql.SQL("PUBLIC")

#: The schema name `public` *is* an ordinary identifier.
PUBLIC_SCHEMA = sql.Identifier("public")


def owner_and_login_role_statements(db_name: str, db_user: str, password: str) -> List[Statement]:
    """The owning group role, its login role, and the membership grant."""

    return [
        (
            sql.SQL("CREATE ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN").format(
                role=sql.Identifier(db_name)
            ),
            None,
        ),
        (
            # The password is a bound parameter, so it never becomes part of the
            # statement text and cannot leak through logs or a traceback.
            # psycopg2 interpolates client side, which is why this works in DDL
            # (psycopg3 and asyncpg bind server side and would reject it).
            sql.SQL(
                "CREATE ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT LOGIN ENCRYPTED PASSWORD %s"
            ).format(role=sql.Identifier(db_user)),
            (password,),
        ),
        (
            sql.SQL("GRANT {group} TO {member}").format(group=sql.Identifier(db_name), member=sql.Identifier(db_user)),
            None,
        ),
    ]


def create_database_statements(db_name: str, db_user: str) -> List[Statement]:
    """CREATE DATABASE owned by the login role, then close it off from PUBLIC."""

    return [
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


def owner_grant_all_on_public_schema(db_user: str) -> Statement:
    """Lets the new owner hand out rights on its own public schema."""

    return (
        sql.SQL("GRANT ALL ON SCHEMA {schema} TO {role} WITH GRANT OPTION").format(
            schema=PUBLIC_SCHEMA, role=sql.Identifier(db_user)
        ),
        None,
    )


def public_schema_create_statements(db_name: str, db_user: str) -> List[Statement]:
    """Grants CREATE on the public schema to both roles."""

    return [
        (
            sql.SQL("GRANT CREATE ON SCHEMA {schema} TO {role}").format(
                schema=PUBLIC_SCHEMA, role=sql.Identifier(role)
            ),
            None,
        )
        for role in (db_name, db_user)
    ]


def shared_readonly_statements(role: str) -> List[Statement]:
    """Grants SELECT on the shared schema, now and for tables added later."""

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


def grant_connect_statement(shared_db: str, role: str) -> Statement:
    """Opens the shared database to a role."""

    return (
        sql.SQL("GRANT CONNECT ON DATABASE {shared} TO {role}").format(
            shared=sql.Identifier(shared_db), role=sql.Identifier(role)
        ),
        None,
    )


def login_role_statement(user_name: str, password: str) -> Statement:
    """A single login role, e.g. the read-only shared user."""

    return (
        sql.SQL("CREATE ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT LOGIN ENCRYPTED PASSWORD %s").format(
            role=sql.Identifier(user_name)
        ),
        (password,),
    )


def alter_role_password_statement(role: str, password: str) -> Statement:
    """Replaces the password of an existing login role."""

    return (
        sql.SQL("ALTER ROLE {role} ENCRYPTED PASSWORD %s").format(role=sql.Identifier(role)),
        (password,),
    )


def shared_readonly_revoke_statements(role: str) -> List[Statement]:
    """Undoes :func:`shared_readonly_statements`, in reverse order.

    The default privileges go first: they are recorded per granting role, so this
    has to run as the same role that granted them - the shared owner.
    """

    return [
        (
            sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} REVOKE SELECT ON TABLES FROM {role}").format(
                schema=PUBLIC_SCHEMA, role=sql.Identifier(role)
            ),
            None,
        ),
        (
            sql.SQL("REVOKE SELECT ON ALL TABLES IN SCHEMA {schema} FROM {role}").format(
                schema=PUBLIC_SCHEMA, role=sql.Identifier(role)
            ),
            None,
        ),
    ]


def revoke_connect_statement(shared_db: str, role: str) -> Statement:
    """Closes the shared database to a role."""

    return (
        sql.SQL("REVOKE CONNECT ON DATABASE {shared} FROM {role}").format(
            shared=sql.Identifier(shared_db), role=sql.Identifier(role)
        ),
        None,
    )


def harden_shared_schema_statements(schema_owner: str) -> List[Statement]:
    """Stops everyone but the shared owner from creating objects in the shared schema."""

    return [
        (
            sql.SQL("REVOKE CREATE ON SCHEMA {schema} FROM {public}").format(schema=PUBLIC_SCHEMA, public=PUBLIC_ROLE),
            None,
        ),
        (
            sql.SQL("GRANT CREATE ON SCHEMA {schema} TO {role}").format(
                schema=PUBLIC_SCHEMA, role=sql.Identifier(schema_owner)
            ),
            None,
        ),
    ]


def drop_role_statement(role: str) -> Statement:
    """Drops a role if it exists."""

    return (
        sql.SQL("DROP ROLE IF EXISTS {role}").format(role=sql.Identifier(role)),
        None,
    )


def terminate_backends_statement(db_name: str) -> Statement:
    """Disconnects every other session from a database, so that it can be dropped.

    Note:
        This is a ``SELECT`` but it is not read-only - it must go through
        ``_execute_all`` like any other statement, or a dry run would cut live
        connections while claiming to have changed nothing.
    """

    return (
        sql.SQL(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()"
        ),
        (db_name,),
    )


def drop_database_statement(db_name: str) -> Statement:
    """Drops a database if it exists."""

    return (
        sql.SQL("DROP DATABASE IF EXISTS {database}").format(database=sql.Identifier(db_name)),
        None,
    )
