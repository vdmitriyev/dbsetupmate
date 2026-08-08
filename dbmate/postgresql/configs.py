import os


class PostgreSQLConfig:
    """Mate configs for the database"""

    # PostgreSQL to store data
    POSTGRESQL_DB_HOST = os.environ.get("POSTGRESQL_DB_HOST") or "localhost"
    POSTGRESQL_DB_HOST_PORT = os.environ.get("POSTGRESQL_DB_HOST_PORT") or "5432"
    POSTGRESQL_DB_NAME = os.environ.get("POSTGRESQL_DB_NAME") or "postgres"
    POSTGRESQL_ADMIN_USER = os.environ.get("POSTGRESQL_ADMIN_USER") or "postgres"
    POSTGRESQL_ADMIN_PASSWORD = os.environ.get("POSTGRESQL_ADMIN_PASSWORD") or "dbmate"

    # demo database
    POSTGRESQL_DEMO_DB = os.environ.get("POSTGRESQL_DEMO_DB") or "dbmate_db_demo"
    POSTGRESQL_DEMO_USER = os.environ.get("POSTGRESQL_DEMO_USER") or "dbmate_user_demo"
    POSTGRESQL_DEMO_PASSWORD = os.environ.get("POSTGRESQL_DEMO_PASSWORD") or "dbmate"

    POSTGRESQL_DEMO_USER_READONLY = os.environ.get("POSTGRESQL_DEMO_USER_READONLY") or "dbmate_user_demo_ro"
    POSTGRESQL_DEMO_USER_READONLY_PASSWORD = os.environ.get("POSTGRESQL_DEMO_USER_READONLY_PASSWORD") or "dbmate"

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)


database_config = PostgreSQLConfig()
