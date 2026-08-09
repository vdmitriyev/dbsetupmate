"""PostgreSQL backend of dbmate.

Note:
    Modules inside this package import from concrete submodules
    (``from dbmate.postgresql.manager import PostgresMate``) and never from this
    package or from ``dbmate`` itself, so that re-exports here cannot create an
    import cycle.
"""

from dbmate.postgresql.configs import PostgreSQLConfig
from dbmate.postgresql.connection import connect
from dbmate.postgresql.functions import (
    create_db,
    create_shared_db,
    create_user_readonly,
    show_next_db_name,
)
from dbmate.postgresql.identifiers import normalize_identifier
from dbmate.postgresql.manager import PostgresMate
from dbmate.postgresql.models import CreatedDatabase, DatabaseNames

__all__ = [
    "PostgresMate",
    "PostgreSQLConfig",
    "CreatedDatabase",
    "DatabaseNames",
    "connect",
    "normalize_identifier",
    "create_db",
    "create_shared_db",
    "create_user_readonly",
    "show_next_db_name",
]
