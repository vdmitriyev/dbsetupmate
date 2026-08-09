"""Module level convenience wrappers around :class:`PostgresMate`.

Use these when a single call is all you need; hold a
:class:`~dbmate.postgresql.manager.PostgresMate` instead when you make several
calls against the same configuration.

Every wrapper propagates :class:`~dbmate.exceptions.DBMateException` - none of
them swallow errors.
"""

from typing import Optional

from dbmate.postgresql.configs import PostgreSQLConfig
from dbmate.postgresql.manager import PostgresMate
from dbmate.postgresql.models import CreatedDatabase, DatabaseNames


def create_database(  # pylint: disable=too-many-arguments
    db_name: str,
    db_user: str,
    db_password: str,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
    grant_demo_access: bool = True,
) -> CreatedDatabase:
    """Creates a database, its owning group role and a login role for it.

    See :meth:`PostgresMate.create_database`.

    Args:
        db_name (str): name of the new database, also used for the owning group role
        db_user (str): name of the login role that owns the database
        db_password (str): password for the login role
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them
        grant_demo_access (bool): also grant read-only access to the demo database

    Returns:
        CreatedDatabase: what was created
    """

    return PostgresMate(config, dry_run=dry_run).create_database(
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        grant_demo_access=grant_demo_access,
    )


def create_readonly_user(
    user_name: Optional[str] = None,
    password: Optional[str] = None,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> str:
    """Creates a role with read-only access to the shared demo database.

    See :meth:`PostgresMate.create_readonly_user`.

    Args:
        user_name (str, optional): role to create. Defaults to the configured read-only user.
        password (str, optional): its password. Defaults to the configured one.
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them

    Returns:
        str: the normalised role name
    """

    return PostgresMate(config, dry_run=dry_run).create_readonly_user(user_name=user_name, password=password)


def init_demo_database(
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> CreatedDatabase:
    """Creates the shared demo database and hardens its schema.

    See :meth:`PostgresMate.init_demo_database`.

    Args:
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them

    Returns:
        CreatedDatabase: what was created
    """

    return PostgresMate(config, dry_run=dry_run).init_demo_database()


def next_database_names(*, config: Optional[PostgreSQLConfig] = None) -> DatabaseNames:
    """Derives the next free auto-generated database and user names.

    See :meth:`PostgresMate.next_database_names`.

    Args:
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.

    Returns:
        DatabaseNames: the next free names and the number they are built from
    """

    return PostgresMate(config).next_database_names()
