"""Small, connection-agnostic helpers for the PostgreSQL backend.

These are pure functions with no dependency on :class:`PostgresMate` or on any
open connection, kept apart from the manager so the orchestration code stays
free of low-level detail.
"""

from typing import Optional

import psycopg2
from psycopg2 import sql

from dbmate.exceptions import DBMateException, exception_for_pgcode


def translate_error(error: psycopg2.Error, message: str) -> DBMateException:
    """Maps a driver error onto the matching dbmate exception.

    Args:
        error (psycopg2.Error): the original driver error
        message (str): context describing what dbmate was trying to do

    Returns:
        DBMateException: an instance of the most specific matching subclass
    """

    pgcode = getattr(error, "pgcode", None)
    pgerror = getattr(error, "pgerror", None)
    exception_class = exception_for_pgcode(pgcode)
    details = (pgerror or str(error)).strip()

    return exception_class(f"{message}: {details}", pgcode=pgcode, pgerror=pgerror)


def render_statement(statement: sql.Composable, cursor) -> str:
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


def require_password(password: Optional[str], role: str) -> None:
    """Rejects an empty password before it reaches the server."""

    if not password:
        raise DBMateException(f"A password is required for the role '{role}'")
