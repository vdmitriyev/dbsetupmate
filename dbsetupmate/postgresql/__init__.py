"""PostgreSQL backend of dbsetupmate.

Note:
    Modules inside this package import from concrete submodules
    (``from dbsetupmate.postgresql.manager import PostgresMate``) and never from this
    package or from ``dbsetupmate`` itself, so that re-exports here cannot create an
    import cycle.
"""

from dbsetupmate.postgresql.configs import PostgreSQLConfig
from dbsetupmate.postgresql.connection import connect
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
from dbsetupmate.postgresql.identifiers import normalize_identifier
from dbsetupmate.postgresql.manager import PostgresMate
from dbsetupmate.postgresql.models import CreatedDatabase, DatabaseNames, ManagedDatabase

__all__ = [
    "PostgresMate",
    "PostgreSQLConfig",
    "CreatedDatabase",
    "DatabaseNames",
    "ManagedDatabase",
    "connect",
    "normalize_identifier",
    "create_db",
    "create_shared_db",
    "create_shared_user_readonly",
    "drop_db",
    "drop_user",
    "grant_shared_access",
    "list_dbs",
    "list_users",
    "revoke_shared_access",
    "set_user_password",
    "show_next_db_name",
]
