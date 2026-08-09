"""Provides module specific constants."""

import os
from pathlib import Path

BASEDIR = os.path.join(Path(__file__).resolve().parent.parent)
CLI_NAME = "dbmate"
APP_NAME = "dbmate"
LOGGER_NAME = "dbmate"
LOG_FILE_NAME = "dbmate.log"
LOG_FILE_PATH = os.path.join(BASEDIR, LOG_FILE_NAME)
DEFAULT_LOG_LEVEL = "INFO"

# Defaults for `PostgreSQLConfig`. They are plain literals on purpose: every
# environment variable is read at call time by `PostgreSQLConfig.from_env()`, so
# that `--env-file` (loaded well after this module is imported) takes effect.
DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = 5432
DEFAULT_DB_NAME = "postgres"
DEFAULT_ADMIN_USER = "postgres"
# The password fallbacks below are documented placeholders for a local sandbox,
# not credentials: any real deployment sets the matching POSTGRESQL_* variable.
DEFAULT_ADMIN_PASSWORD = "dbmate"  # nosec B105
DEFAULT_DEMO_DB = "dbmate_db_demo"
DEFAULT_DEMO_USER = "dbmate_user_demo"
DEFAULT_DEMO_PASSWORD = "dbmate"  # nosec B105
DEFAULT_DEMO_USER_READONLY = "dbmate_user_demo_ro"
DEFAULT_DEMO_USER_READONLY_PASSWORD = "dbmate"  # nosec B105
DEFAULT_DB_PREFIX = "dbmate_db"
DEFAULT_USER_PREFIX = "dbmate_user"
DEFAULT_CONNECT_TIMEOUT = 5

# PostgreSQL truncates identifiers at NAMEDATALEN - 1 bytes instead of failing,
# which silently breaks any later "connect to the database by name" step.
MAX_IDENTIFIER_BYTES = 63


def app_log_level() -> str:
    """Reads the configured log level from the environment.

    Read at call time rather than at import time, so a level provided through
    ``--env-file`` is honoured.

    Returns:
        str: the log level name, upper cased. Defaults to ``"INFO"``.
    """

    return os.environ.get("APP_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
