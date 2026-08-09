"""Tests for PostgreSQLConfig."""

import pytest

from dbmate.exceptions import DBMateException
from dbmate.postgresql.configs import PostgreSQLConfig


def test_defaults_when_the_environment_is_empty():
    config = PostgreSQLConfig.from_env({})

    assert config.host == "localhost"
    assert config.port == 5432
    assert config.database == "postgres"
    assert config.admin_user == "postgres"
    assert config.shared_db == "dbmate_db_shared"
    assert config.db_prefix == "dbmate_db"


def test_reads_every_setting_from_the_environment():
    config = PostgreSQLConfig.from_env(
        {
            "POSTGRESQL_DB_HOST": "db.internal",
            "POSTGRESQL_DB_HOST_PORT": "6543",
            "POSTGRESQL_DB_NAME": "maintenance",
            "POSTGRESQL_ADMIN_USER": "root",
            "POSTGRESQL_ADMIN_PASSWORD": "root-secret",
            "POSTGRESQL_SHARED_DB": "shared",
            "POSTGRESQL_SHARED_USER": "shared_owner",
            "POSTGRESQL_SHARED_PASSWORD": "shared-secret",
            "POSTGRESQL_SHARED_USER_READONLY": "shared_ro",
            "POSTGRESQL_SHARED_USER_READONLY_PASSWORD": "ro-secret",
            "POSTGRESQL_DB_PREFIX": "course_db",
            "POSTGRESQL_USER_PREFIX": "course_user",
            "POSTGRESQL_CONNECT_TIMEOUT": "11",
        }
    )

    assert config.host == "db.internal"
    assert config.port == 6543
    assert config.database == "maintenance"
    assert config.admin_user == "root"
    assert config.admin_password == "root-secret"
    assert config.shared_db == "shared"
    assert config.shared_user_readonly == "shared_ro"
    assert config.shared_user_readonly_password == "ro-secret"
    assert config.db_prefix == "course_db"
    assert config.user_prefix == "course_user"
    assert config.connect_timeout == 11


def test_an_empty_value_falls_back_to_the_default():
    config = PostgreSQLConfig.from_env({"POSTGRESQL_DB_HOST": ""})

    assert config.host == "localhost"


def test_the_port_is_an_integer():
    config = PostgreSQLConfig.from_env({"POSTGRESQL_DB_HOST_PORT": "5433"})

    assert config.port == 5433
    assert isinstance(config.port, int)


@pytest.mark.parametrize("value", ["not-a-port", "54.32"])
def test_a_non_numeric_port_is_rejected(value):
    with pytest.raises(DBMateException, match="must be an integer"):
        PostgreSQLConfig.from_env({"POSTGRESQL_DB_HOST_PORT": value})


def test_a_non_numeric_timeout_is_rejected():
    with pytest.raises(DBMateException, match="POSTGRESQL_CONNECT_TIMEOUT"):
        PostgreSQLConfig.from_env({"POSTGRESQL_CONNECT_TIMEOUT": "soon"})


def test_the_environment_is_read_when_from_env_is_called(monkeypatch):
    # This is what makes `--env-file`, loaded after import, take effect.
    monkeypatch.setenv("POSTGRESQL_DB_HOST", "late.example")

    assert PostgreSQLConfig.from_env().host == "late.example"


def test_repr_does_not_leak_passwords():
    config = PostgreSQLConfig(
        admin_password="admin-secret",
        shared_password="shared-secret",
        shared_user_readonly_password="ro-secret",
    )
    rendered = repr(config)

    assert "admin-secret" not in rendered
    assert "shared-secret" not in rendered
    assert "ro-secret" not in rendered
    assert "localhost" in rendered


def test_a_config_can_be_built_without_touching_the_environment():
    config = PostgreSQLConfig(host="db.internal", admin_user="root", admin_password="root-secret")

    assert (config.host, config.admin_user) == ("db.internal", "root")
