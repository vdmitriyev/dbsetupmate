"""Connection handling for the PostgreSQL backend.

Every connection in dbsetupmate is opened through :func:`connect`, so that closing and
error translation happen in exactly one place.
"""

from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extensions import cursor as Psycopg2Cursor

from dbsetupmate.configs import logger
from dbsetupmate.postgresql.configs import PostgreSQLConfig
from dbsetupmate.postgresql.helpers import translate_error


@contextmanager
def connect(
    config: PostgreSQLConfig,
    database: str,
    user: str,
    password: str,
    autocommit: bool = True,
) -> Iterator[Psycopg2Cursor]:
    """Opens a connection and yields a cursor, closing both afterwards.

    Args:
        config (PostgreSQLConfig): host, port and timeout settings
        database (str): database to connect to
        user (str): role to connect as
        password (str): password for that role
        autocommit (bool): ``True`` for statements that cannot run inside a
            transaction (``CREATE DATABASE``). When ``False`` the block is
            committed on a clean exit and rolled back on failure.

    Yields:
        psycopg2.extensions.cursor: a cursor on the open connection

    Raises:
        DBSetupMateException: for any driver error, including failures to connect
    """

    try:
        connection = psycopg2.connect(
            dbname=database,
            user=user,
            password=password,
            host=config.host,
            port=config.port,
            connect_timeout=config.connect_timeout,
            application_name=config.application_name,
        )
    except psycopg2.Error as ex:
        raise translate_error(ex, f"Could not connect to database '{database}' as '{user}'") from ex

    cursor = None
    try:
        connection.autocommit = autocommit
        cursor = connection.cursor()
        yield cursor
        if not autocommit:
            connection.commit()
    except psycopg2.Error as ex:
        _rollback(connection, autocommit)
        raise translate_error(ex, f"Error while working with database '{database}' as '{user}'") from ex
    except BaseException:
        _rollback(connection, autocommit)
        raise
    finally:
        _close(cursor, "cursor")
        _close(connection, "connection")
        logger.debug("PostgreSQL connection to '%s' was closed", database)


def _rollback(connection, autocommit: bool) -> None:
    """Rolls a failed transaction back, never masking the original error."""

    if autocommit:
        return
    try:
        connection.rollback()
    except psycopg2.Error as ex:  # pragma: no cover - defensive
        logger.debug("Rollback failed and was ignored: %s", ex)


def _close(resource, kind: str) -> None:
    """Closes a cursor or connection, never masking the original error."""

    if resource is None:
        return
    try:
        resource.close()
    except psycopg2.Error as ex:  # pragma: no cover - defensive
        logger.debug("Closing the %s failed and was ignored: %s", kind, ex)
