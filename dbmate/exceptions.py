"""Provides module specific exceptions."""


class DBMateException(Exception):
    """Generic exception for DBMateException."""


class DBUserAlreadyExistsException(DBMateException):
    """Raised when a database user with the given name already exists."""


class DBUserNotExistsException(DBMateException):
    """Raised when a database user with the given name does not exist."""
