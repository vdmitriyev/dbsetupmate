"""Return values of the dbmate PostgreSQL API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseNames:
    """The next free auto-generated database and user names.

    Attributes:
        database (str): name for the new database, e.g. ``dbmate_db_03``
        user (str): name for the new login role, e.g. ``dbmate_user_03``
        order (int): the number both names were built from
    """

    database: str
    user: str
    order: int


@dataclass(frozen=True)
class CreatedDatabase:
    """What a call to ``create_db`` actually produced.

    Attributes:
        database (str): the normalised database name
        owner_role (str): the group role owning the database (NOLOGIN)
        login_role (str): the role able to log in
        granted_demo_access (bool): whether read-only access to the demo database was granted
        dry_run (bool): ``True`` when nothing was executed against the server
    """

    database: str
    owner_role: str
    login_role: str
    granted_demo_access: bool = False
    dry_run: bool = False
