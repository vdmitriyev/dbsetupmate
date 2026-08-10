"""Tests for PostgresMate."""

import pytest
from psycopg2 import errorcodes, sql

from dbmate.exceptions import (
    DatabaseAlreadyExistsException,
    DatabaseNotExistsException,
    DBMateException,
    DBUserAlreadyExistsException,
    DBUserNotExistsException,
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


def test_list_dbs_reports_the_prefixed_databases_with_their_owners(mate, server):
    server.databases = ["course_db_02", "course_db_01", "postgres"]
    server.database_owners = {"course_db_01": "course_user_01"}

    databases = mate.list_dbs()

    assert [(item.database, item.owner) for item in databases] == [
        ("course_db_01", "course_user_01"),
        ("course_db_02", "admin"),
    ]


def test_list_dbs_ignores_databases_outside_the_prefix(mate, server):
    server.databases = ["postgres", "template1", "unrelated_db_01"]

    assert mate.list_dbs() == []


def test_list_users_reports_only_the_prefixed_roles(mate, server):
    server.roles = ["course_user_02", "course_user_01", "admin", "shared_ro"]

    assert mate.list_users() == ["course_user_01", "course_user_02"]


def test_the_listing_queries_are_anchored_and_parameterised(mate, server):
    mate.list_users()

    statement = server.executed[0]
    assert "left(rolname::text" in statement.text
    assert statement.params == {"length": len("course_user_"), "prefix": "course_user_"}


# ----------------------------------------------------------------------
# create_db
# ----------------------------------------------------------------------


def test_create_db_runs_the_expected_statements_in_order(mate, server):
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    ddl = server.ddl_texts()
    assert len(ddl) == 8
    assert "CREATE ROLE " in ddl[0] and "NOLOGIN" in ddl[0]
    assert "CREATE ROLE " in ddl[1] and "LOGIN ENCRYPTED PASSWORD %s" in ddl[1]
    assert ddl[2].startswith("Composed([SQL('GRANT ')")
    assert "CREATE DATABASE" in ddl[3]
    assert "REVOKE ALL ON DATABASE" in ddl[4]
    assert "GRANT ALL ON SCHEMA" in ddl[5]
    assert "GRANT CREATE ON SCHEMA" in ddl[6]
    assert "GRANT CREATE ON SCHEMA" in ddl[7]


def test_create_db_returns_what_it_created(mate):
    created = mate.create_db("course_db_01", "course_user_01", "s3cret")

    assert created.database == "course_db_01"
    assert created.owner_role == "course_db_01"
    assert created.login_role == "course_user_01"
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


def test_create_db_does_not_grant_shared_access(mate, server):
    # Shared access is now a separate call, so create_db must not touch it.
    mate.create_db("course_db_01", "course_user_01", "s3cret")

    assert not [item for item in server.executed if "GRANT CONNECT ON DATABASE" in item.text]
    assert not [item for item in server.executed if "ALL TABLES IN SCHEMA" in item.text]


def test_grant_shared_access_grants_connect_and_select(mate, server):
    mate.grant_shared_access("course_user_01")

    connect_grants = [item for item in server.executed if "GRANT CONNECT ON DATABASE" in item.text]
    assert connect_grants

    shared_grants = [item for item in server.executed if "ALL TABLES IN SCHEMA" in item.text]
    assert shared_grants
    assert any("ALTER DEFAULT PRIVILEGES" in item.text for item in server.executed)
    # The read-only grants run as the shared owner, inside the shared database.
    assert all(item.database == "shared_db" and item.user == "shared_user" for item in shared_grants)


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
    PostgresMate(config, dry_run=True).create_shared_user_readonly()

    assert server.ddl() == []


# ----------------------------------------------------------------------
# read-only user, shared database
# ----------------------------------------------------------------------


def test_create_shared_user_readonly_defaults_to_the_configured_role(mate, server):
    created_user = mate.create_shared_user_readonly()

    assert created_user == "shared_ro"
    assert [item for item in server.executed if "LOGIN ENCRYPTED PASSWORD" in item.text][0].params == ("ro-secret",)


def test_create_shared_user_readonly_grants_connect_and_select(mate, server):
    mate.create_shared_user_readonly("reader", "reader-secret")

    ddl = server.ddl_texts()
    assert any("GRANT CONNECT ON DATABASE" in item for item in ddl)
    assert any("GRANT SELECT ON ALL TABLES IN SCHEMA" in item for item in ddl)
    assert any("ALTER DEFAULT PRIVILEGES" in item for item in ddl)


def test_create_shared_user_readonly_does_not_harden_the_shared_schema(mate, server):
    # Hardening is part of bootstrapping the shared database, not of adding a reader.
    mate.create_shared_user_readonly("reader", "reader-secret")

    assert not [item for item in server.executed if "REVOKE CREATE ON SCHEMA" in item.text]


def test_harden_shared_schema_revokes_create_from_public(mate, server):
    mate.harden_shared_schema()

    ddl = server.ddl()
    assert len(ddl) == 2
    assert "REVOKE CREATE ON SCHEMA" in ddl[0].text and "SQL('PUBLIC')" in ddl[0].text
    assert "GRANT CREATE ON SCHEMA" in ddl[1].text
    assert all(item.database == "shared_db" for item in ddl)


def test_create_shared_db_does_not_grant_the_shared_database_to_itself(mate, server):
    created = mate.create_shared_db()

    assert created.database == "shared_db"
    assert not [item for item in server.executed if "GRANT CONNECT ON DATABASE" in item.text]
    assert [item for item in server.executed if "REVOKE CREATE ON SCHEMA" in item.text]


def test_create_shared_db_never_connects_as_the_shared_user_before_it_exists(mate, server):
    mate.create_shared_db()

    shared_user_connections = [item for item in server.connections if item.user == "shared_user"]
    # Only the connection the new owner makes to its own database.
    assert all(item.database == "shared_db" for item in shared_user_connections)


def test_grant_public_schema_rights_targets_the_new_database(mate, server):
    mate.grant_public_schema_rights("course_db_01", "course_user_01")

    ddl = server.ddl()
    assert len(ddl) == 2
    assert all(item.database == "course_db_01" and item.user == "admin" for item in ddl)


def test_revoke_shared_access_undoes_exactly_what_the_grant_did(mate, server):
    mate.revoke_shared_access("course_user_01")

    ddl = server.ddl_texts()
    assert len(ddl) == 3
    # Reverse of the grant: the SELECT privileges first, CONNECT last.
    assert "ALTER DEFAULT PRIVILEGES" in ddl[0] and "REVOKE SELECT ON TABLES" in ddl[0]
    assert "REVOKE SELECT ON ALL TABLES IN SCHEMA" in ddl[1]
    assert "REVOKE CONNECT ON DATABASE" in ddl[2]


def test_the_shared_privileges_are_revoked_by_the_role_that_granted_them(mate, server):
    mate.revoke_shared_access("course_user_01")

    # Default privileges are recorded per granting role, so only the shared owner
    # can take them back - admin revoking them would be a silent no-op.
    revokes = [item for item in server.executed if "ALTER DEFAULT PRIVILEGES" in item.text]
    assert all(item.database == "shared_db" and item.user == "shared_user" for item in revokes)

    connect_revoke = [item for item in server.executed if "REVOKE CONNECT ON DATABASE" in item.text][0]
    assert connect_revoke.user == "admin"


def test_revoke_shared_access_keeps_the_role_itself(mate, server):
    mate.revoke_shared_access("course_user_01")

    assert not [item for item in server.executed if "DROP ROLE" in item.text]


# ----------------------------------------------------------------------
# passwords
# ----------------------------------------------------------------------


def test_set_user_password_binds_the_new_password_as_a_parameter(mate, server):
    changed = mate.set_user_password("course_user_01", "n3w-secret")

    assert changed == "course_user_01"
    altered = [item for item in server.executed if "ALTER ROLE" in item.text]
    assert len(altered) == 1
    assert "ENCRYPTED PASSWORD %s" in altered[0].text
    assert altered[0].params == ("n3w-secret",)
    assert all("n3w-secret" not in item.text for item in server.executed)


def test_set_user_password_does_not_check_that_the_role_exists(mate, server):
    # ALTER ROLE answers with SQLSTATE 42704 itself; a preflight would be a
    # second round trip that adds nothing.
    mate.set_user_password("course_user_01", "n3w-secret")

    assert not [item for item in server.executed if "FROM pg_roles" in item.text]


@pytest.mark.parametrize("password", ["", None])
def test_set_user_password_rejects_an_empty_password_without_connecting(mate, server, password):
    with pytest.raises(DBMateException, match="password is required"):
        mate.set_user_password("course_user_01", password)

    assert server.connections == []


# ----------------------------------------------------------------------
# dropping
# ----------------------------------------------------------------------


def test_drop_db_terminates_the_open_sessions_before_dropping(mate, server):
    server.databases = ["course_db_01"]

    mate.drop_db("course_db_01", "course_user_01")

    texts = server.texts()
    terminate = [index for index, text in enumerate(texts) if "pg_terminate_backend" in text][0]
    dropped = [index for index, text in enumerate(texts) if "DROP DATABASE" in text][0]

    # PostgreSQL refuses to drop a database anyone is still connected to.
    assert terminate < dropped


def test_drop_db_drops_the_login_role_before_the_group_role(mate, server):
    server.databases = ["course_db_01"]

    mate.drop_db("course_db_01", "course_user_01")

    dropped = [item.text for item in server.executed if "DROP ROLE" in item.text]
    assert len(dropped) == 2
    # The login role is a member of the group role, so it goes first.
    assert "course_user_01" in dropped[0]
    assert "course_db_01" in dropped[1]


def test_drop_db_only_drops_the_group_role_when_no_login_role_is_named(mate, server):
    server.databases = ["course_db_01"]

    mate.drop_db("course_db_01")

    dropped = [item.text for item in server.executed if "DROP ROLE" in item.text]
    assert len(dropped) == 1
    assert "course_db_01" in dropped[0]


def test_drop_database_runs_on_an_autocommitting_connection(mate, server):
    server.databases = ["course_db_01"]

    mate.drop_db("course_db_01")

    dropped = [item for item in server.executed if "DROP DATABASE" in item.text][0]
    connection = [item for item in server.connections if item.database == dropped.database][-1]

    # DROP DATABASE cannot run inside a transaction block.
    assert connection.autocommit is True


def test_dropping_a_database_that_is_not_there_is_rejected(mate, server):
    with pytest.raises(DatabaseNotExistsException, match="course_db_01"):
        mate.drop_db("course_db_01")

    assert server.ddl() == []
    assert not [item for item in server.executed if "pg_terminate_backend" in item.text]


def test_a_dry_run_drops_nothing_and_terminates_nothing(config, server):
    server.databases = ["course_db_01"]

    PostgresMate(config, dry_run=True).drop_db("course_db_01", "course_user_01")

    # `ddl()` filters SELECTs out, and pg_terminate_backend is one - so the whole
    # statement log has to be checked, not just the DDL.
    assert not [item for item in server.executed if "pg_terminate_backend" in item.text]
    assert server.ddl() == []


def test_drop_user_drops_the_role(mate, server):
    server.roles = ["course_user_01"]

    mate.drop_user("course_user_01")

    ddl = server.ddl_texts()
    assert len(ddl) == 1
    assert "DROP ROLE IF EXISTS" in ddl[0] and "course_user_01" in ddl[0]


def test_dropping_a_role_that_is_not_there_is_rejected(mate, server):
    # DROP ROLE IF EXISTS would report success, which reads as "it was dropped".
    with pytest.raises(DBUserNotExistsException, match="course_user_01"):
        mate.drop_user("course_user_01")

    assert server.ddl() == []


@pytest.mark.parametrize("name", ["", "my-db", "1bad"])
def test_dropping_an_unusable_name_is_rejected_without_connecting(mate, server, name):
    with pytest.raises(InvalidIdentifierException):
        mate.drop_db(name)

    assert server.connections == []
