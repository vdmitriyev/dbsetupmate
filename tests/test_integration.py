"""End-to-end tests against a live PostgreSQL.

These are skipped by default. Start a server and run them explicitly::

    docker compose -f compose-tests.yaml up -d database-15
    POSTGRESQL_DB_HOST_PORT=5415 pytest -m integration

Mocked tests prove dbmate builds the SQL it means to build; only these prove
PostgreSQL accepts it and that the resulting privileges are what was intended.
"""

from dataclasses import replace

import pytest

from dbmate.exceptions import (
    DatabaseAlreadyExistsException,
    DBConnectionException,
    DBMateException,
    InsufficientPrivilegeException,
)
from dbmate.postgresql.configs import PostgreSQLConfig
from dbmate.postgresql.connection import connect
from dbmate.postgresql.manager import PostgresMate

pytestmark = pytest.mark.integration

DB_NAME = "dbmate_it_db_01"
DB_USER = "dbmate_it_user_01"
DB_PASSWORD = "dbmate-it-secret"  # nosec B105
READONLY_USER = "dbmate_it_ro"
READONLY_PASSWORD = "dbmate-it-ro"  # nosec B105


def _admin(config, database=None):
    return connect(
        config,
        database=database or config.database,
        user=config.admin_user,
        password=config.admin_password,
    )


def _drop_everything(config):
    """Removes anything a previous run may have left behind, ignoring failures."""

    names = [f'DROP DATABASE IF EXISTS "{name}"' for name in (DB_NAME, config.shared_db)]
    names += [
        f'DROP ROLE IF EXISTS "{role}"'
        for role in (DB_USER, DB_NAME, READONLY_USER, config.shared_user, config.shared_db)
    ]

    for statement in names:
        try:
            with _admin(config) as cursor:
                # The names are fixed literals defined above, never user input.
                cursor.execute(statement)  # nosec B608
        except DBMateException:
            pass


@pytest.fixture(name="live_config", scope="module")
def live_config_fixture():
    """A config pointing at a reachable server, or a skip."""

    config = PostgreSQLConfig.from_env()
    try:
        with _admin(config) as cursor:
            cursor.execute("SELECT 1;")
    except DBMateException as ex:
        pytest.skip(f"no PostgreSQL reachable at {config.host}:{config.port} ({ex})")

    _drop_everything(config)
    yield config
    _drop_everything(config)


@pytest.fixture(name="mate", scope="module")
def mate_fixture(live_config):
    mate = PostgresMate(live_config)
    mate.create_shared_db()

    return mate


def test_the_shared_database_is_created(mate, live_config):
    assert mate.database_exists(live_config.shared_db) is True
    assert mate.user_exists(live_config.shared_user) is True


def test_create_db_end_to_end(mate):
    created = mate.create_db(DB_NAME, DB_USER, DB_PASSWORD)

    assert created.database == DB_NAME
    assert mate.database_exists(DB_NAME) is True
    assert mate.user_exists(DB_USER) is True


def test_the_new_user_owns_its_own_schema(live_config):
    with connect(live_config, database=DB_NAME, user=DB_USER, password=DB_PASSWORD) as cursor:
        cursor.execute("CREATE TABLE owned_by_me (id integer);")
        cursor.execute("INSERT INTO owned_by_me VALUES (1);")
        cursor.execute("SELECT count(*) FROM owned_by_me;")

        assert cursor.fetchone()[0] == 1


def test_creating_the_same_database_twice_is_rejected(mate):
    with pytest.raises(DatabaseAlreadyExistsException):
        mate.create_db(DB_NAME, DB_USER, DB_PASSWORD)


def test_show_next_db_name_continues_after_what_already_exists(live_config):
    mate = PostgresMate(replace(live_config, db_prefix="dbmate_it_db", user_prefix="dbmate_it_user"))

    names = mate.show_next_db_name()

    assert (names.database, names.order) == ("dbmate_it_db_02", 2)


def test_a_readonly_user_can_read_the_shared_database(mate, live_config):
    with connect(
        live_config,
        database=live_config.shared_db,
        user=live_config.shared_user,
        password=live_config.shared_password,
    ) as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS shared_data (id integer);")
        cursor.execute("INSERT INTO shared_data VALUES (42);")

    mate.create_user_readonly(READONLY_USER, READONLY_PASSWORD)

    with connect(live_config, database=live_config.shared_db, user=READONLY_USER, password=READONLY_PASSWORD) as cursor:
        cursor.execute("SELECT id FROM shared_data;")

        assert cursor.fetchone()[0] == 42


def test_a_readonly_user_cannot_write_to_the_shared_database(live_config):
    # The translated exception is raised when the block exits, so pytest.raises wraps it.
    with pytest.raises(InsufficientPrivilegeException):
        with connect(
            live_config, database=live_config.shared_db, user=READONLY_USER, password=READONLY_PASSWORD
        ) as cursor:
            cursor.execute("INSERT INTO shared_data VALUES (43);")


def test_a_wrong_password_is_reported_as_a_connection_error(live_config):
    with pytest.raises(DBConnectionException):
        with connect(live_config, database=live_config.shared_db, user=DB_USER, password="wrong"):
            pass
