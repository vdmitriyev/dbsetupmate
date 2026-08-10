"""Module level convenience wrappers around :class:`PostgresMate`.

Use these when a single call is all you need; hold a
:class:`~dbsetupmate.postgresql.manager.PostgresMate` instead when you make several
calls against the same configuration.

Every wrapper propagates :class:`~dbsetupmate.exceptions.DBSetupMateException` - none of
them swallow errors.
"""

from typing import List, Optional

from dbsetupmate.postgresql.configs import PostgreSQLConfig
from dbsetupmate.postgresql.manager import PostgresMate
from dbsetupmate.postgresql.models import CreatedDatabase, DatabaseNames, ManagedDatabase


def create_db(
    db_name: str,
    db_user: str,
    db_password: str,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> CreatedDatabase:
    """Creates a database, its owning group role and a login role for it.

    See :meth:`PostgresMate.create_db`.

    Args:
        db_name (str): name of the new database, also used for the owning group role
        db_user (str): name of the login role that owns the database
        db_password (str): password for the login role
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them

    Returns:
        CreatedDatabase: what was created
    """

    return PostgresMate(config, dry_run=dry_run).create_db(
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
    )


def grant_shared_access(
    role: str,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> None:
    """Grants a role read-only access to the shared database.

    See :meth:`PostgresMate.grant_shared_access`.

    Args:
        role (str): the role to grant read-only shared access to
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them
    """

    PostgresMate(config, dry_run=dry_run).grant_shared_access(role)


def revoke_shared_access(
    role: str,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> None:
    """Takes a role's read-only access to the shared database back.

    See :meth:`PostgresMate.revoke_shared_access`.

    Args:
        role (str): the role to revoke shared access from
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them
    """

    PostgresMate(config, dry_run=dry_run).revoke_shared_access(role)


def set_user_password(
    user_name: str,
    password: str,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> str:
    """Replaces the password of an existing login role.

    See :meth:`PostgresMate.set_user_password`.

    Args:
        user_name (str): the role to change
        password (str): its new password
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them

    Returns:
        str: the normalised role name
    """

    return PostgresMate(config, dry_run=dry_run).set_user_password(user_name, password)


def create_shared_user_readonly(
    user_name: Optional[str] = None,
    password: Optional[str] = None,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> str:
    """Creates a login role and grants it read-only access to the shared database.

    See :meth:`PostgresMate.create_shared_user_readonly`.

    Args:
        user_name (str, optional): role to create. Defaults to the configured read-only user.
        password (str, optional): its password. Defaults to the configured one.
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them

    Returns:
        str: the normalised role name
    """

    return PostgresMate(config, dry_run=dry_run).create_shared_user_readonly(user_name=user_name, password=password)


def create_shared_db(
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> CreatedDatabase:
    """Creates the shared database and hardens its schema.

    See :meth:`PostgresMate.create_shared_db`.

    Args:
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them

    Returns:
        CreatedDatabase: what was created
    """

    return PostgresMate(config, dry_run=dry_run).create_shared_db()


def show_next_db_name(*, config: Optional[PostgreSQLConfig] = None) -> DatabaseNames:
    """Derives the next free auto-generated database and user names.

    See :meth:`PostgresMate.show_next_db_name`.

    Args:
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.

    Returns:
        DatabaseNames: the next free names and the number they are built from
    """

    return PostgresMate(config).show_next_db_name()


def list_dbs(*, config: Optional[PostgreSQLConfig] = None) -> List[ManagedDatabase]:
    """Lists the databases built from the configured prefix, with their owners.

    See :meth:`PostgresMate.list_dbs`.

    Args:
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.

    Returns:
        List[ManagedDatabase]: the matching databases, ordered by name
    """

    return PostgresMate(config).list_dbs()


def list_users(*, config: Optional[PostgreSQLConfig] = None) -> List[str]:
    """Lists the roles built from the configured user prefix.

    See :meth:`PostgresMate.list_users`.

    Args:
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.

    Returns:
        List[str]: the matching role names, ordered by name
    """

    return PostgresMate(config).list_users()


def drop_db(
    db_name: str,
    db_user: Optional[str] = None,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> None:
    """Drops a database, its owning group role and, when given, its login role.

    See :meth:`PostgresMate.drop_db`.

    Args:
        db_name (str): the database to drop, and the name of its owning group role
        db_user (str, optional): the login role to drop with it
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them
    """

    PostgresMate(config, dry_run=dry_run).drop_db(db_name, db_user)


def drop_user(
    user_name: str,
    *,
    config: Optional[PostgreSQLConfig] = None,
    dry_run: bool = False,
) -> None:
    """Drops a role.

    See :meth:`PostgresMate.drop_user`.

    Args:
        user_name (str): the role to drop
        config (PostgreSQLConfig, optional): connection settings. Defaults to the environment.
        dry_run (bool): report the statements instead of executing them
    """

    PostgresMate(config, dry_run=dry_run).drop_user(user_name)
