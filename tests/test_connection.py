"""Tests for the connection context manager."""

import pytest
from psycopg2 import errorcodes

from dbsetupmate.exceptions import DatabaseAlreadyExistsException, DBConnectionException, DBSetupMateException
from dbsetupmate.postgresql.connection import connect
from tests.fakes import FakeError


def _open(config, server, **kwargs):
    return connect(config, database="postgres", user="admin", password="admin-secret", **kwargs)


def test_passes_the_configured_connection_settings(config, server):
    with _open(config, server):
        pass

    connection = server.connections[0]
    assert (connection.database, connection.user) == ("postgres", "admin")


def test_closes_the_cursor_and_the_connection(config, server):
    with _open(config, server) as cursor:
        cursor.execute("SELECT 1;")

    connection = server.connections[0]
    assert connection.closed is True
    assert all(item.closed for item in connection.cursors)


def test_closes_the_connection_even_when_the_body_fails(config, server):
    with pytest.raises(DBSetupMateException):
        with _open(config, server) as cursor:
            cursor.execute("SELECT 1;")
            raise FakeError("boom", pgcode=errorcodes.DUPLICATE_DATABASE)

    connection = server.connections[0]
    assert connection.closed is True
    assert connection.cursors[0].closed is True


def test_autocommit_is_the_default(config, server):
    with _open(config, server):
        pass

    assert server.connections[0].autocommit is True


def test_a_transactional_block_commits_on_success(config, server):
    with _open(config, server, autocommit=False) as cursor:
        cursor.execute("SELECT 1;")

    connection = server.connections[0]
    assert connection.autocommit is False
    assert (connection.commits, connection.rollbacks) == (1, 0)


def test_a_transactional_block_rolls_back_on_failure(config, server):
    server.statement_errors["CREATE ROLE"] = FakeError("boom", pgcode=errorcodes.DUPLICATE_OBJECT)

    with pytest.raises(DBSetupMateException):
        with _open(config, server, autocommit=False) as cursor:
            cursor.execute("CREATE ROLE x")

    connection = server.connections[0]
    assert (connection.commits, connection.rollbacks) == (0, 1)


def test_a_failure_to_connect_is_translated(config, server):
    server.connect_errors["postgres"] = FakeError("could not connect to server")

    with pytest.raises(DBConnectionException, match="Could not connect to database 'postgres' as 'admin'"):
        with _open(config, server):
            pass


def test_a_statement_error_is_translated_to_its_sqlstate(config, server):
    server.statement_errors["CREATE DATABASE"] = FakeError(
        "boom", pgcode=errorcodes.DUPLICATE_DATABASE, pgerror='database "x" already exists'
    )

    with pytest.raises(DatabaseAlreadyExistsException) as caught:
        with _open(config, server) as cursor:
            cursor.execute("CREATE DATABASE x")

    assert caught.value.pgcode == errorcodes.DUPLICATE_DATABASE


def test_a_non_driver_error_passes_through_untouched(config, server):
    with pytest.raises(ValueError):
        with _open(config, server):
            raise ValueError("not a database problem")

    assert server.connections[0].closed is True
