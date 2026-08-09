"""`dbmate` - creates and maintains PostgreSQL databases, users and grants.

Beyond the ``dbmate`` command line interface, this package is usable as a library:

    >>> from dbmate import PostgresMate, PostgreSQLConfig
    >>> mate = PostgresMate(PostgreSQLConfig(host="db.internal", admin_password="..."))
    >>> created = mate.create_database("course_db_01", "course_user_01", "s3cret")

Every name listed in ``__all__`` is resolved lazily (PEP 562), so ``import dbmate``
stays cheap and the submodules never have to import this module back.
"""

import importlib
from typing import TYPE_CHECKING, Any, Dict, List

#: public name -> module that defines it
_EXPORTS: Dict[str, str] = {
    "PostgresMate": "dbmate.postgresql.manager",
    "PostgreSQLConfig": "dbmate.postgresql.configs",
    "CreatedDatabase": "dbmate.postgresql.models",
    "DatabaseNames": "dbmate.postgresql.models",
    "create_database": "dbmate.postgresql.functions",
    "create_readonly_user": "dbmate.postgresql.functions",
    "init_demo_database": "dbmate.postgresql.functions",
    "next_database_names": "dbmate.postgresql.functions",
    "DBMateException": "dbmate.exceptions",
    "DBConnectionException": "dbmate.exceptions",
    "DBUserAlreadyExistsException": "dbmate.exceptions",
    "DBUserNotExistsException": "dbmate.exceptions",
    "DatabaseAlreadyExistsException": "dbmate.exceptions",
    "DatabaseNotExistsException": "dbmate.exceptions",
    "InsufficientPrivilegeException": "dbmate.exceptions",
    "InvalidIdentifierException": "dbmate.exceptions",
    "DBOperationException": "dbmate.exceptions",
}

__all__ = ["__version__", *_EXPORTS]


def __getattr__(name: str) -> Any:
    """Resolves a public name on first use (PEP 562)."""

    if name == "__version__":
        from dbmate.version import package_version  # pylint: disable=import-outside-toplevel

        value = package_version()
    elif name in _EXPORTS:
        value = getattr(importlib.import_module(_EXPORTS[name]), name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    globals()[name] = value

    return value


def __dir__() -> List[str]:
    return sorted(__all__)


if TYPE_CHECKING:  # pragma: no cover - for type checkers and IDEs only
    from dbmate.exceptions import (
        DatabaseAlreadyExistsException,
        DatabaseNotExistsException,
        DBConnectionException,
        DBMateException,
        DBOperationException,
        DBUserAlreadyExistsException,
        DBUserNotExistsException,
        InsufficientPrivilegeException,
        InvalidIdentifierException,
    )
    from dbmate.postgresql.configs import PostgreSQLConfig
    from dbmate.postgresql.functions import (
        create_database,
        create_readonly_user,
        init_demo_database,
        next_database_names,
    )
    from dbmate.postgresql.manager import PostgresMate
    from dbmate.postgresql.models import CreatedDatabase, DatabaseNames
