import os
import traceback
from dataclasses import dataclass, field

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.configs import logger


@dataclass
class DatabaseConfig:
    """A dataclass to store database connection details from environment variables."""

    DB_USER: str = field(default_factory=lambda: os.environ.get("POSTGRES_USER"))
    DB_PASSWORD: str = field(default_factory=lambda: os.environ.get("POSTGRES_PASSWORD"))
    DB_NAME: str = field(default_factory=lambda: os.environ.get("POSTGRES_DB"))
    DB_BACKEND: str = field(default_factory=lambda: os.environ.get("POSTGRES_DB_HOST"))
    DB_PORT: int = field(default_factory=lambda: int(os.environ.get("POSTGRES_DB_HOST_PORT", 5432)))

    def connection_string(self) -> str:
        """Constructs and returns the database connection string."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_BACKEND}:{self.DB_PORT}/{self.DB_NAME}"

    def __str__(self) -> str:
        """Constructs and returns the database connection string without credentials."""
        return f"postgresql://{self.DB_USER}:***@{self.DB_BACKEND}:{self.DB_PORT}/{self.DB_NAME}"


def test_connect_to_database() -> str:
    """Connects to a  database.
    Returns:
        str: version of the database
    """
    db_config = DatabaseConfig()

    connection, message = None, ""

    try:
        connection = psycopg2.connect(
            user=db_config.DB_USER,
            password=db_config.DB_PASSWORD,
            host=db_config.DB_BACKEND,
            port=db_config.DB_PORT,
            database=db_config.DB_NAME,
        )

        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        logger.debug("PostgreSQL DNS parameters: {0}".format(connection.get_dsn_parameters(), "\n"))
        cursor.execute("SELECT version();")
        record = cursor.fetchone()
        message = f"Connected to database: {record[0]}"

    except (Exception, psycopg2.Error) as ex:
        message = f"Error while working with database. Database: '{db_config.DB_NAME}'"
        logger.error(f"{message}. Exception: {ex}", exc_info=True)
    finally:
        if connection:
            cursor.close()
            connection.close()
            logger.debug(f"PostgreSQL connection was closed. Database: '{db_config}'")
        else:
            logger.warning(f"PostgreSQL connection is None. Not able to close. Database: '{db_config}'")

    return message
