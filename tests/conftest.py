"""Shared fixtures."""

import pytest

from dbmate.postgresql import connection as connection_module
from dbmate.postgresql.configs import PostgreSQLConfig
from tests.fakes import FakeServer


@pytest.fixture(name="server")
def server_fixture(monkeypatch) -> FakeServer:
    """Replaces psycopg2.connect with the fake server for the duration of a test."""

    server = FakeServer()
    monkeypatch.setattr(connection_module.psycopg2, "connect", server.connect)

    return server


@pytest.fixture(name="config")
def config_fixture() -> PostgreSQLConfig:
    """A config with predictable, non-default values."""

    return PostgreSQLConfig(
        host="db.test",
        port=6543,
        database="postgres",
        admin_user="admin",
        admin_password="admin-secret",
        demo_db="demo_db",
        demo_user="demo_user",
        demo_password="demo-secret",
        demo_user_readonly="demo_ro",
        demo_user_readonly_password="ro-secret",
        db_prefix="course_db",
        user_prefix="course_user",
    )
