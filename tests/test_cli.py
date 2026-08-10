"""The command line interface.

These cover the behaviour that lives in the commands themselves rather than in
:class:`PostgresMate` - the confirmation gate on the destructive commands, the
masking in ``show-config``, and that a failure exits non-zero.
"""

import pytest
from typer.testing import CliRunner

from dbsetupmate import cli
from dbsetupmate.commands import postgresql as postgresql_module
from dbsetupmate.configs import settings
from dbsetupmate.postgresql.manager import PostgresMate

ADMIN_PASSWORD = "admin-secret"  # nosec B105


@pytest.fixture(name="runner")
def runner_fixture(config, server, monkeypatch) -> CliRunner:  # pylint: disable=unused-argument
    """A runner whose commands talk to the fake server through the test config."""

    # The CLI opts into file logging; a test must not drop a dbsetupmate.log in the cwd.
    monkeypatch.setattr(cli, "configure_logging", lambda *args, **kwargs: None)
    # `settings.dry_run` is set by the root callback, so it is read per call.
    monkeypatch.setattr(postgresql_module, "_mate", lambda: PostgresMate(config, dry_run=settings.dry_run))

    return CliRunner()


# ----------------------------------------------------------------------
# the confirmation gate
# ----------------------------------------------------------------------


def test_a_declined_drop_changes_nothing(runner, server):
    server.databases = ["course_db_01"]

    result = runner.invoke(cli.app, ["pg", "drop-db", "--db-name", "course_db_01"], input="n\n")

    assert result.exit_code != 0
    assert server.executed == []


def test_a_confirmed_drop_goes_ahead(runner, server):
    server.databases = ["course_db_01"]

    result = runner.invoke(cli.app, ["pg", "drop-db", "--db-name", "course_db_01"], input="y\n")

    assert result.exit_code == 0
    assert [item for item in server.executed if "DROP DATABASE" in item.text]


def test_yes_skips_the_prompt(runner, server):
    server.databases = ["course_db_01"]

    result = runner.invoke(cli.app, ["pg", "drop-db", "--db-name", "course_db_01", "--yes"])

    assert result.exit_code == 0
    assert [item for item in server.executed if "DROP DATABASE" in item.text]


def test_a_dry_run_needs_no_confirmation_because_it_changes_nothing(runner, server):
    server.databases = ["course_db_01"]

    result = runner.invoke(cli.app, ["--dry-run", "pg", "drop-db", "--db-name", "course_db_01"])

    assert result.exit_code == 0
    assert server.ddl() == []
    assert not [item for item in server.executed if "pg_terminate_backend" in item.text]


def test_dropping_a_user_is_gated_too(runner, server):
    server.roles = ["course_user_01"]

    result = runner.invoke(cli.app, ["pg", "drop-user", "--user-name", "course_user_01"], input="n\n")

    assert result.exit_code != 0
    assert server.ddl() == []


# ----------------------------------------------------------------------
# show-config
# ----------------------------------------------------------------------


def test_show_config_never_prints_a_password(runner, monkeypatch):
    monkeypatch.setenv("POSTGRESQL_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("POSTGRESQL_SHARED_PASSWORD", "shared-secret")
    monkeypatch.setenv("POSTGRESQL_SHARED_USER_READONLY_PASSWORD", "ro-secret")

    result = runner.invoke(cli.app, ["pg", "show-config"])

    assert result.exit_code == 0
    assert ADMIN_PASSWORD not in result.stdout
    assert "shared-secret" not in result.stdout
    assert "ro-secret" not in result.stdout
    assert result.stdout.count(postgresql_module.MASKED) == 3


def test_show_config_prints_the_settings_that_are_not_secret(runner, monkeypatch):
    monkeypatch.setenv("POSTGRESQL_DB_HOST", "db.test")
    monkeypatch.setenv("POSTGRESQL_DB_PREFIX", "course_db")

    result = runner.invoke(cli.app, ["pg", "show-config"])

    assert "db.test" in result.stdout
    assert "course_db" in result.stdout


def test_show_config_reports_an_unusable_port_instead_of_crashing(runner, monkeypatch):
    monkeypatch.setenv("POSTGRESQL_DB_HOST_PORT", "not-a-number")

    result = runner.invoke(cli.app, ["pg", "show-config"])

    assert result.exit_code == 1
    assert "POSTGRESQL_DB_HOST_PORT" in result.stdout


# ----------------------------------------------------------------------
# the rest of the surface
# ----------------------------------------------------------------------


def test_show_dbs_prints_what_the_manager_found(runner, server):
    server.databases = ["course_db_01"]
    server.database_owners = {"course_db_01": "course_user_01"}

    result = runner.invoke(cli.app, ["pg", "show-dbs"])

    assert result.exit_code == 0
    assert "course_db_01" in result.stdout
    assert "course_user_01" in result.stdout


def test_show_dbs_says_so_when_there_is_nothing_to_show(runner):
    result = runner.invoke(cli.app, ["pg", "show-dbs"])

    assert result.exit_code == 0
    assert "No database" in result.stdout


def test_the_readonly_command_is_only_reachable_under_its_new_name(runner):
    assert runner.invoke(cli.app, ["pg", "create-shared-user-readonly", "--help"]).exit_code == 0
    # Renamed in 0.6.0 with no alias.
    assert runner.invoke(cli.app, ["pg", "create-user-readonly", "--help"]).exit_code != 0


def test_set_user_password_takes_the_password_without_prompting_for_it(runner, server):
    result = runner.invoke(
        cli.app,
        ["pg", "set-user-password", "--user-name", "course_user_01", "--password", "n3w-secret"],
    )

    assert result.exit_code == 0
    assert [item for item in server.executed if "ALTER ROLE" in item.text]
    assert "n3w-secret" not in result.stdout


def test_a_dbsetupmate_failure_exits_with_code_one(runner):
    result = runner.invoke(
        cli.app,
        ["pg", "set-user-password", "--user-name", "1bad", "--password", "s3cret"],
    )

    assert result.exit_code == 1
    assert "✖" in result.stdout
