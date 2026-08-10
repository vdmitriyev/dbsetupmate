"""Provides module specific constants."""

import os
from pathlib import Path

BASEDIR = os.path.join(Path(__file__).resolve().parent.parent)
CLI_NAME = "dbsetupmate"
APP_NAME = "dbsetupmate"
LOGGER_NAME = "dbsetupmate"
LOG_FILE_NAME = "dbsetupmate.log"
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
DEFAULT_ADMIN_PASSWORD = "dbsetupmate"  # nosec B105
DEFAULT_SHARED_DB = "dbsetupmate_db_shared"
DEFAULT_SHARED_USER = "dbsetupmate_user_shared"
DEFAULT_SHARED_PASSWORD = "dbsetupmate"  # nosec B105
DEFAULT_SHARED_USER_READONLY = "dbsetupmate_user_shared_ro"
DEFAULT_SHARED_USER_READONLY_PASSWORD = "dbsetupmate"  # nosec B105
DEFAULT_DB_PREFIX = "dbsetupmate_db"
DEFAULT_USER_PREFIX = "dbsetupmate_user"
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
