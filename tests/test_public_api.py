"""The import surface other libraries are meant to rely on."""

import importlib

import dbsetupmate
from dbsetupmate.postgresql.models import CreatedDatabase


def test_the_client_and_its_config_are_importable_from_the_root():
    from dbsetupmate import PostgresMate, PostgreSQLConfig  # pylint: disable=import-outside-toplevel

    assert PostgresMate(PostgreSQLConfig(host="db.test")).config.host == "db.test"


def test_the_exceptions_are_importable_from_the_root():
    from dbsetupmate import DBSetupMateException, InvalidIdentifierException  # pylint: disable=import-outside-toplevel

    assert issubclass(InvalidIdentifierException, DBSetupMateException)


def test_every_advertised_name_resolves():
    for name in dbsetupmate.__all__:
        assert getattr(dbsetupmate, name) is not None, name


def test_dir_lists_the_public_names():
    assert set(dir(dbsetupmate)) == set(dbsetupmate.__all__)


def test_an_unknown_attribute_still_raises():
    try:
        dbsetupmate.does_not_exist  # pylint: disable=pointless-statement
    except AttributeError as ex:
        assert "does_not_exist" in str(ex)
    else:
        raise AssertionError("expected an AttributeError")


def test_the_version_is_exposed():
    assert isinstance(dbsetupmate.__version__, str)


def test_the_subpackage_exposes_the_same_api():
    postgresql = importlib.import_module("dbsetupmate.postgresql")

    for name in postgresql.__all__:
        assert getattr(postgresql, name) is not None, name


def test_the_convenience_functions_delegate_to_the_client(config, server):
    from dbsetupmate import create_db  # pylint: disable=import-outside-toplevel

    created = create_db("course_db_01", "course_user_01", "s3cret", config=config)

    assert isinstance(created, CreatedDatabase)
    assert created.database == "course_db_01"
    assert server.ddl()


def test_the_old_function_names_are_gone():
    functions = importlib.import_module("dbsetupmate.postgresql.functions")

    for removed in [
        "create_postgresql_db",
        "grand_rights_to_own_public_schema",
        "new_postgresql_db_names",
        "init_postgresql_with_demo_user",
        "create_postgresql_readonly_user_for_demo_db",
        # Renamed to line the library API up with the CLI command names.
        "create_database",
        "create_readonly_user",
        "init_demo_database",
        "next_database_names",
        # Renamed when the "demo" database became the "shared" database.
        "create_demo_db",
        # Renamed to name the database the read-only access is granted on.
        "create_user_readonly",
    ]:
        assert not hasattr(functions, removed), removed
