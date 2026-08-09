"""Connection settings for the PostgreSQL backend."""

import os
from dataclasses import dataclass, field
from typing import Mapping, Optional

from dbmate.constants import (
    APP_NAME,
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USER,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_DB_HOST,
    DEFAULT_DB_NAME,
    DEFAULT_DB_PORT,
    DEFAULT_DB_PREFIX,
    DEFAULT_DEMO_DB,
    DEFAULT_DEMO_PASSWORD,
    DEFAULT_DEMO_USER,
    DEFAULT_DEMO_USER_READONLY,
    DEFAULT_DEMO_USER_READONLY_PASSWORD,
    DEFAULT_USER_PREFIX,
)
from dbmate.exceptions import DBMateException


def _read(env: Mapping[str, str], key: str, default: str) -> str:
    """Reads a setting, treating an empty value as "not set"."""

    return env.get(key) or default


@dataclass(frozen=True)
class PostgreSQLConfig:  # pylint: disable=too-many-instance-attributes
    """Connection settings used by :class:`dbmate.postgresql.manager.PostgresMate`.

    Build one explicitly to drive dbmate from another library, or call
    :meth:`from_env` to read the usual ``POSTGRESQL_*`` environment variables.

    Note:
        Password fields are excluded from ``repr()``, but that does **not** protect
        them from ``dataclasses.asdict()``, pickling or a traceback showing locals.
    """

    host: str = DEFAULT_DB_HOST
    port: int = DEFAULT_DB_PORT
    database: str = DEFAULT_DB_NAME
    admin_user: str = DEFAULT_ADMIN_USER
    admin_password: str = field(default=DEFAULT_ADMIN_PASSWORD, repr=False)

    # shared read-only "demo" database
    demo_db: str = DEFAULT_DEMO_DB
    demo_user: str = DEFAULT_DEMO_USER
    demo_password: str = field(default=DEFAULT_DEMO_PASSWORD, repr=False)
    demo_user_readonly: str = DEFAULT_DEMO_USER_READONLY
    demo_user_readonly_password: str = field(default=DEFAULT_DEMO_USER_READONLY_PASSWORD, repr=False)

    # naming of auto-generated databases and users
    db_prefix: str = DEFAULT_DB_PREFIX
    user_prefix: str = DEFAULT_USER_PREFIX

    connect_timeout: int = DEFAULT_CONNECT_TIMEOUT
    application_name: str = APP_NAME

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "PostgreSQLConfig":
        """Builds a config from environment variables.

        The environment is read when this method is called, not when the module is
        imported, so variables loaded from an ``--env-file`` are picked up.

        Args:
            env (Mapping[str, str], optional): mapping to read from. Defaults to ``os.environ``.

        Returns:
            PostgreSQLConfig: settings, falling back to the documented defaults

        Raises:
            DBMateException: if ``POSTGRESQL_DB_HOST_PORT`` is not an integer
        """

        env = os.environ if env is None else env

        raw_port = _read(env, "POSTGRESQL_DB_HOST_PORT", str(DEFAULT_DB_PORT))
        try:
            port = int(raw_port)
        except (TypeError, ValueError) as ex:
            raise DBMateException(f"POSTGRESQL_DB_HOST_PORT must be an integer, got {raw_port!r}") from ex

        raw_timeout = _read(env, "POSTGRESQL_CONNECT_TIMEOUT", str(DEFAULT_CONNECT_TIMEOUT))
        try:
            connect_timeout = int(raw_timeout)
        except (TypeError, ValueError) as ex:
            raise DBMateException(f"POSTGRESQL_CONNECT_TIMEOUT must be an integer, got {raw_timeout!r}") from ex

        return cls(
            host=_read(env, "POSTGRESQL_DB_HOST", DEFAULT_DB_HOST),
            port=port,
            database=_read(env, "POSTGRESQL_DB_NAME", DEFAULT_DB_NAME),
            admin_user=_read(env, "POSTGRESQL_ADMIN_USER", DEFAULT_ADMIN_USER),
            admin_password=_read(env, "POSTGRESQL_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
            demo_db=_read(env, "POSTGRESQL_DEMO_DB", DEFAULT_DEMO_DB),
            demo_user=_read(env, "POSTGRESQL_DEMO_USER", DEFAULT_DEMO_USER),
            demo_password=_read(env, "POSTGRESQL_DEMO_PASSWORD", DEFAULT_DEMO_PASSWORD),
            demo_user_readonly=_read(env, "POSTGRESQL_DEMO_USER_READONLY", DEFAULT_DEMO_USER_READONLY),
            demo_user_readonly_password=_read(
                env, "POSTGRESQL_DEMO_USER_READONLY_PASSWORD", DEFAULT_DEMO_USER_READONLY_PASSWORD
            ),
            db_prefix=_read(env, "POSTGRESQL_DB_PREFIX", DEFAULT_DB_PREFIX),
            user_prefix=_read(env, "POSTGRESQL_USER_PREFIX", DEFAULT_USER_PREFIX),
            connect_timeout=connect_timeout,
        )
