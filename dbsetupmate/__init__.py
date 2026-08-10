"""`dbsetupmate` - creates and maintains PostgreSQL databases, users and grants.

Beyond the ``dbsetupmate`` command line interface, this package is usable as a library:

    >>> from dbsetupmate import PostgresMate, PostgreSQLConfig
    >>> mate = PostgresMate(PostgreSQLConfig(host="db.internal", admin_password="..."))
    >>> created = mate.create_db("course_db_01", "course_user_01", "s3cret")

Every name listed in ``__all__`` is resolved lazily (PEP 562), so ``import dbsetupmate``
stays cheap and the submodules never have to import this module back.
"""

import importlib
from typing import TYPE_CHECKING, Any, Dict, List

#: public name -> module that defines it
_EXPORTS: Dict[str, str] = {
    "PostgresMate": "dbsetupmate.postgresql.manager",
    "PostgreSQLConfig": "dbsetupmate.postgresql.configs",
    "CreatedDatabase": "dbsetupmate.postgresql.models",
    "DatabaseNames": "dbsetupmate.postgresql.models",
    "ManagedDatabase": "dbsetupmate.postgresql.models",
    "create_db": "dbsetupmate.postgresql.functions",
    "create_shared_db": "dbsetupmate.postgresql.functions",
    "create_shared_user_readonly": "dbsetupmate.postgresql.functions",
    "drop_db": "dbsetupmate.postgresql.functions",
    "drop_user": "dbsetupmate.postgresql.functions",
    "grant_shared_access": "dbsetupmate.postgresql.functions",
    "list_dbs": "dbsetupmate.postgresql.functions",
    "list_users": "dbsetupmate.postgresql.functions",
    "revoke_shared_access": "dbsetupmate.postgresql.functions",
    # nosec B105: the value is the defining module, not a password.
    "set_user_password": "dbsetupmate.postgresql.functions",  # nosec B105
    "show_next_db_name": "dbsetupmate.postgresql.functions",
    "DBSetupMateException": "dbsetupmate.exceptions",
    "DBConnectionException": "dbsetupmate.exceptions",
    "DBUserAlreadyExistsException": "dbsetupmate.exceptions",
    "DBUserNotExistsException": "dbsetupmate.exceptions",
    "DatabaseAlreadyExistsException": "dbsetupmate.exceptions",
    "DatabaseNotExistsException": "dbsetupmate.exceptions",
    "InsufficientPrivilegeException": "dbsetupmate.exceptions",
    "InvalidIdentifierException": "dbsetupmate.exceptions",
    "DBOperationException": "dbsetupmate.exceptions",
}

__all__ = ["__version__", *_EXPORTS]


def __getattr__(name: str) -> Any:
    """Resolves a public name on first use (PEP 562)."""

    if name == "__version__":
        from dbsetupmate.version import package_version  # pylint: disable=import-outside-toplevel

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
    from dbsetupmate.exceptions import (
        DatabaseAlreadyExistsException,
        DatabaseNotExistsException,
        DBConnectionException,
        DBSetupMateException,
        DBOperationException,
        DBUserAlreadyExistsException,
        DBUserNotExistsException,
        InsufficientPrivilegeException,
        InvalidIdentifierException,
    )
    from dbsetupmate.postgresql.configs import PostgreSQLConfig
    from dbsetupmate.postgresql.functions import (
        create_db,
        create_shared_db,
        create_shared_user_readonly,
        drop_db,
        drop_user,
        grant_shared_access,
        list_dbs,
        list_users,
        revoke_shared_access,
        set_user_password,
        show_next_db_name,
    )
    from dbsetupmate.postgresql.manager import PostgresMate
    from dbsetupmate.postgresql.models import CreatedDatabase, DatabaseNames, ManagedDatabase
