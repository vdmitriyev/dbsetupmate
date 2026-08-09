"""Tests for PostgresMate."""

import pytest
from psycopg2 import errorcodes, sql

from dbmate.exceptions import (
    DatabaseAlreadyExistsException,
    DBMateException,
    DBUserAlreadyExistsException,
    InvalidIdentifierException,
)
from dbmate.postgresql.manager import PostgresMate
from tests.fakes import FakeError


@pytest.fixture(name="mate")
def mate_fixture(config, server):  # pylint: disable=unused-argument
    return PostgresMate(config)


# ----------------------------------------------------------------------
# inspection
# ----------------------------------------------------------------------


def test_database_exists(mate, server):
    server.databases = ["course_db_01"]

    assert mate.database_exists("course_db_01") is True
    assert mate.database_exists("course_db_02") is False


def test_user_exists(mate, server):
    server.roles = ["course_user_01"]

    assert mate.user_exists("course_user_01") is True
    assert mate.user_exists("nobody") is False


def test_show_next_db_name_starts_at_one_on_an_empty_server(mate):
    names = mate.show_next_db_name()

    assert (names.database, names.user, names.order) == ("course_db_01", "course_user_01", 1)


def test_show_next_db_name_continues_after_the_highest_number(mate, server):
    server.databases = ["course_db_01", "course_db_02", "course_db_07"]

    names = mate.show_next_db_name()

    # `count(*) + 1` would have produced course_db_04 and collided forever.
    assert (names.database, names.user, names.order) == ("course_db_08", "course_user_08", 8)


def test_show_next_db_name_ignores_unrelated_databases(mate, server):
    server.databases = ["course_db_01", "course_db_backup", "postgres"]

    assert mate.show_next_db_name().order == 2


def test_show_next_db_name_query_is_anchored_and_parameterised(mate, server):
    mate.show_next_db_name()

    statement = server.executed[0]
    assert "left(datname::text" in statement.text
    assert statement.params == {"length": len("course_db_"), "prefix": "course_db_"}


# ----------------------------------------------------------------------
# create_db
# ----------------------------------------------------------------------


def test_create_db_runs_the_expected_statements_in_order(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    ddl = server.ddl_texts()
    assert len(ddl) == 11
    assert "CREATE ROLE " in ddl[0] and "NOLOGIN" in ddl[0]
    assert "CREATE ROLE " in ddl[1] and "LOGIN ENCRYPTED PASSWORD %s" in ddl[1]
    assert ddl[2].startswith("Composed([SQL('GRANT ')")
    assert "CREATE DATABASE" in ddl[3]
    assert "REVOKE ALL ON DATABASE" in ddl[4]
    assert "GRANT CONNECT ON DATABASE" in ddl[5]
    assert "GRANT ALL ON SCHEMA" in ddl[6]
    assert "GRANT CREATE ON SCHEMA" in ddl[7]
    assert "GRANT CREATE ON SCHEMA" in ddl[8]
    assert "GRANT SELECT ON ALL TABLES IN SCHEMA" in ddl[9]
    assert "ALTER DEFAULT PRIVILEGES" in ddl[10]


def test_create_db_returns_what_it_created(mate):
    created = mate.create_db("course_db_01", "course_user_01", "s3cret")

    assert created.database == "course_db_01"
    assert created.owner_role == "course_db_01"
    assert created.login_role == "course_user_01"
    assert created.granted_demo_access is True
    assert created.dry_run is False


def test_the_password_is_a_bound_parameter_and_never_appears_in_the_sql(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    create_login_role = [item for item in server.executed if "LOGIN ENCRYPTED PASSWORD" in item.text]
    assert len(create_login_role) == 1
    assert create_login_role[0].params == ("s3cret",)

    # The secret must not be reachable through any statement dbmate built.
    assert all("s3cret" not in item.text for item in server.executed)


def test_identifiers_are_quoted_rather_than_interpolated(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    create_db_statement = [item for item in server.executed if "CREATE DATABASE" in item.text][0]
    expected = sql.SQL("CREATE DATABASE {database} WITH OWNER = {owner}").format(
        database=sql.Identifier("course_db_01"), owner=sql.Identifier("course_user_01")
    )

    assert create_db_statement.statement == expected


def test_public_is_emitted_as_a_keyword_not_as_an_identifier(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    revoke = [item for item in server.executed if "REVOKE ALL ON DATABASE" in item.text][0]

    # Identifier('public') would make PostgreSQL look for a role named "public".
    assert "SQL('PUBLIC')" in revoke.text
    assert "Identifier('public')" not in revoke.text


def test_the_two_roles_are_created_in_one_transaction(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    transactional = [item for item in server.connections if item.autocommit is False]
    assert len(transactional) == 1
    assert transactional[0].commits == 1


def test_create_db_uses_autocommit_for_the_create_database_statement(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    owner = [item for item in server.executed if "CREATE DATABASE" in item.text][0]
    connection = [item for item in server.connections if item.database == owner.database][0]

    assert connection.autocommit is True


def test_schema_rights_are_granted_from_inside_the_new_database(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    grant_all = [item for item in server.executed if "GRANT ALL ON SCHEMA" in item.text][0]

    assert grant_all.database == "course_db_01"
    assert grant_all.user == "course_user_01"


def test_demo_grants_run_as_the_demo_owner(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    demo_grants = [item for item in server.executed if "ALL TABLES IN SCHEMA" in item.text]

    assert demo_grants
    assert all(item.database == "demo_db" and item.user == "demo_user" for item in demo_grants)


def test_demo_access_can_be_skipped(mate, server):
    created = mate.create_db("course_db_01", "course_user_01", "s3cret", grant_demo_access=False)

    assert created.granted_demo_access is False
    assert not [item for item in server.executed if "ALL TABLES IN SCHEMA" in item.text]
    assert not [item for item in server.executed if "GRANT CONNECT ON DATABASE" in item.text]


# ----------------------------------------------------------------------
# failure handling
# ----------------------------------------------------------------------


def test_an_existing_database_is_rejected_before_anything_is_created(mate, server):
    server.databases = ["course_db_01"]

    with pytest.raises(DatabaseAlreadyExistsException, match="already exists"):
        mate.create_db("course_db_01", "course_user_01", "s3cret")

    assert server.ddl() == []


def test_an_existing_role_is_rejected_before_anything_is_created(mate, server):
    server.roles = ["course_user_01"]

    with pytest.raises(DBUserAlreadyExistsException, match="course_user_01"):
        mate.create_db("course_db_01", "course_user_01", "s3cret")

    assert server.ddl() == []


def test_a_failed_create_db_rolls_the_roles_back(mate, server):
    server.statement_errors["CREATE DATABASE"] = FakeError(
        "boom", pgcode=errorcodes.INSUFFICIENT_PRIVILEGE, pgerror="permission denied to create database"
    )

    with pytest.raises(DBMateException, match="permission denied"):
        mate.create_db("course_db_01", "course_user_01", "s3cret")

    dropped = [item.text for item in server.executed if "DROP ROLE" in item.text]
    assert len(dropped) == 2
    # The login role is a member of the group role, so it goes first.
    assert "course_user_01" in dropped[0]
    assert "course_db_01" in dropped[1]


def test_a_failed_rollback_does_not_mask_the_original_error(mate, server):
    server.statement_errors["CREATE DATABASE"] = FakeError("boom", pgcode=errorcodes.INSUFFICIENT_PRIVILEGE)
    server.statement_errors["DROP ROLE"] = FakeError("cleanup failed", pgcode=errorcodes.INSUFFICIENT_PRIVILEGE)

    with pytest.raises(DBMateException, match="boom"):
        mate.create_db("course_db_01", "course_user_01", "s3cret")


def test_a_failed_role_creation_leaves_nothing_behind(mate, server):
    server.statement_errors["CREATE ROLE"] = FakeError("boom", pgcode=errorcodes.DUPLICATE_OBJECT)

    with pytest.raises(DBUserAlreadyExistsException):
        mate.create_db("course_db_01", "course_user_01", "s3cret")

    # The transaction is rolled back, so there is nothing to compensate for.
    assert not [item for item in server.executed if "DROP ROLE" in item.text]
    assert server.connections[-1].rollbacks == 1


@pytest.mark.parametrize("name", ["", "my-db", "1bad"])
def test_an_unusable_name_is_rejected_without_connecting(mate, server, name):
    with pytest.raises(InvalidIdentifierException):
        mate.create_db(name, "course_user_01", "s3cret")

    assert server.connections == []


@pytest.mark.parametrize("password", ["", None])
def test_an_empty_password_is_rejected_without_connecting(mate, server, password):
    with pytest.raises(DBMateException, match="password is required"):
        mate.create_db("course_db_01", "course_user_01", password)

    assert server.connections == []


def test_a_mixed_case_name_is_folded_the_way_postgresql_would(mate):
    created = mate.create_db("Course_DB_01", "Course_User_01", "s3cret")

    assert (created.database, created.login_role) == ("course_db_01", "course_user_01")


# ----------------------------------------------------------------------
# dry run
# ----------------------------------------------------------------------


def test_a_dry_run_executes_no_ddl(config, server):
    created = PostgresMate(config, dry_run=True).create_db("course_db_01", "course_user_01", "s3cret")

    assert server.ddl() == []
    assert created.dry_run is True
    assert created.database == "course_db_01"
    assert created.granted_demo_access is False


def test_a_dry_run_still_runs_the_read_only_checks(config, server):
    server.databases = ["course_db_01"]

    with pytest.raises(DatabaseAlreadyExistsException):
        PostgresMate(config, dry_run=True).create_db("course_db_01", "course_user_01", "s3cret")


def test_a_dry_run_reports_the_statements_it_skips(config, server, capsys):
    PostgresMate(config, dry_run=True).create_db("course_db_01", "course_user_01", "s3cret")

    printed = capsys.readouterr().out
    assert "dry-run" in printed
    assert "CREATE DATABASE" in printed
    assert "PASSWORD %s" in printed
    assert "s3cret" not in printed


def test_a_dry_run_readonly_user_executes_no_ddl(config, server):
    PostgresMate(config, dry_run=True).create_user_readonly()

    assert server.ddl() == []


# ----------------------------------------------------------------------
# read-only user, demo database
# ----------------------------------------------------------------------


def test_create_user_readonly_defaults_to_the_configured_role(mate, server):
    created_user = mate.create_user_readonly()

    assert created_user == "demo_ro"
    assert [item for item in server.executed if "LOGIN ENCRYPTED PASSWORD" in item.text][0].params == ("ro-secret",)


def test_create_user_readonly_grants_connect_and_select(mate, server):
    mate.create_user_readonly("reader", "reader-secret")

    ddl = server.ddl_texts()
    assert any("GRANT CONNECT ON DATABASE" in item for item in ddl)
    assert any("GRANT SELECT ON ALL TABLES IN SCHEMA" in item for item in ddl)
    assert any("ALTER DEFAULT PRIVILEGES" in item for item in ddl)


def test_create_user_readonly_does_not_harden_the_demo_schema(mate, server):
    # Hardening is part of bootstrapping the demo database, not of adding a reader.
    mate.create_user_readonly("reader", "reader-secret")

    assert not [item for item in server.executed if "REVOKE CREATE ON SCHEMA" in item.text]


def test_harden_demo_schema_revokes_create_from_public(mate, server):
    mate.harden_demo_schema()

    ddl = server.ddl()
    assert len(ddl) == 2
    assert "REVOKE CREATE ON SCHEMA" in ddl[0].text and "SQL('PUBLIC')" in ddl[0].text
    assert "GRANT CREATE ON SCHEMA" in ddl[1].text
    assert all(item.database == "demo_db" for item in ddl)


def test_create_demo_db_does_not_grant_the_demo_database_to_itself(mate, server):
    created = mate.create_demo_db()

    assert created.database == "demo_db"
    assert not [item for item in server.executed if "GRANT CONNECT ON DATABASE" in item.text]
    assert [item for item in server.executed if "REVOKE CREATE ON SCHEMA" in item.text]


def test_create_demo_db_never_connects_as_the_demo_user_before_it_exists(mate, server):
    mate.create_demo_db()

    demo_user_connections = [item for item in server.connections if item.user == "demo_user"]
    # Only the connection the new owner makes to its own database.
    assert all(item.database == "demo_db" for item in demo_user_connections)


def test_grant_public_schema_rights_targets_the_new_database(mate, server):
    mate.grant_public_schema_rights("course_db_01", "course_user_01")

    ddl = server.ddl()
    assert len(ddl) == 2
    assert all(item.database == "course_db_01" and item.user == "admin" for item in ddl)
