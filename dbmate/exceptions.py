"""Provides module specific exceptions."""

from typing import Dict, Optional, Type

from psycopg2 import errorcodes


class DBMateException(Exception):
    """Generic exception for DBMateException.

    Args:
        message (str): human readable description of the failure
        pgcode (str, optional): the PostgreSQL SQLSTATE of the underlying error, if any
        pgerror (str, optional): the raw error message reported by the server, if any
    """

    def __init__(self, message: str, pgcode: Optional[str] = None, pgerror: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.pgcode = pgcode
        self.pgerror = pgerror


class DBConnectionException(DBMateException):
    """Raised when a connection to the database could not be established."""


class DBUserAlreadyExistsException(DBMateException):
    """Raised when a database user with the given name already exists."""


class DBUserNotExistsException(DBMateException):
    """Raised when a database user with the given name does not exist."""


class DatabaseAlreadyExistsException(DBMateException):
    """Raised when a database with the given name already exists."""


class DatabaseNotExistsException(DBMateException):
    """Raised when a database with the given name does not exist."""


class InsufficientPrivilegeException(DBMateException):
    """Raised when the connected role is not allowed to perform the operation."""


class InvalidIdentifierException(DBMateException):
    """Raised when a database or role name is not a usable PostgreSQL identifier.

    This is a client side validation error, so it never carries a ``pgcode``.
    """


class DBOperationException(DBMateException):
    """Raised for any other error reported by the database driver."""


# SQLSTATE -> exception. Codes are taken from `psycopg2.errorcodes` rather than
# spelled out, so a typo becomes an ImportError instead of a silent mismatch.
EXCEPTION_BY_PGCODE: Dict[str, Type[DBMateException]] = {
    errorcodes.DUPLICATE_OBJECT: DBUserAlreadyExistsException,
    errorcodes.UNDEFINED_OBJECT: DBUserNotExistsException,
    errorcodes.DUPLICATE_DATABASE: DatabaseAlreadyExistsException,
    errorcodes.INVALID_CATALOG_NAME: DatabaseNotExistsException,
    errorcodes.INSUFFICIENT_PRIVILEGE: InsufficientPrivilegeException,
    errorcodes.INVALID_PASSWORD: DBConnectionException,
    errorcodes.INVALID_AUTHORIZATION_SPECIFICATION: DBConnectionException,
}


def exception_for_pgcode(pgcode: Optional[str]) -> Type[DBMateException]:
    """Maps a PostgreSQL SQLSTATE to the matching dbmate exception.

    Args:
        pgcode (str, optional): SQLSTATE reported by the server. ``None`` when the
            driver failed before the server answered (host unreachable, refused, ...).

    Returns:
        Type[DBMateException]: the exception class to raise
    """

    if pgcode is None:
        return DBConnectionException

    return EXCEPTION_BY_PGCODE.get(pgcode, DBOperationException)
