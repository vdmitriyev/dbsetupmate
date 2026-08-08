"""Provides module specific constants."""

import os
from pathlib import Path

BASEDIR = os.path.join(Path(__file__).resolve().parent.parent)
CLI_NAME = "dbmate"
LOGGER_NAME = "dbmate"
LOG_FILE_NAME = "dbmate.log"
APP_LOG_LEVEL = os.environ.get("APP_LOG_LEVEL", "INFO").upper()
LOG_FILE_PATH = os.path.join(BASEDIR, LOG_FILE_NAME)


POSTGRESQL_DB_PREFIX = os.environ.get("POSTGRESQL_DB_PREFIX", "dbmate_db")
POSTGRESQL_USER_PREFIX = os.environ.get("POSTGRESQL_USER_PREFIX", "dbmate_user")
