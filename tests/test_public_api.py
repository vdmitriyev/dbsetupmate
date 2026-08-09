"""The import surface other libraries are meant to rely on."""

import importlib

import dbmate
from dbmate.postgresql.models import CreatedDatabase


def test_the_client_and_its_config_are_importable_from_the_root():
    from dbmate import PostgresMate, PostgreSQLConfig  # pylint: disable=import-outside-toplevel

    assert PostgresMate(PostgreSQLConfig(host="db.test")).config.host == "db.test"


def test_the_exceptions_are_importable_from_the_root():
    from dbmate import DBMateException, InvalidIdentifierException  # pylint: disable=import-outside-toplevel

    assert issubclass(InvalidIdentifierException, DBMateException)


def test_every_advertised_name_resolves():
    for name in dbmate.__all__:
        assert getattr(dbmate, name) is not None, name


def test_dir_lists_the_public_names():
    assert set(dir(dbmate)) == set(dbmate.__all__)


def test_an_unknown_attribute_still_raises():
    try:
        dbmate.does_not_exist  # pylint: disable=pointless-statement
    except AttributeError as ex:
        assert "does_not_exist" in str(ex)
    else:
        raise AssertionError("expected an AttributeError")


def test_the_version_is_exposed():
    assert isinstance(dbmate.__version__, str)


def test_the_subpackage_exposes_the_same_api():
    postgresql = importlib.import_module("dbmate.postgresql")

    for name in postgresql.__all__:
        assert getattr(postgresql, name) is not None, name


def test_the_convenience_functions_delegate_to_the_client(config, server):
    from dbmate import create_database  # pylint: disable=import-outside-toplevel

    created = create_database("course_db_01", "course_user_01", "s3cret", config=config)

    assert isinstance(created, CreatedDatabase)
    assert created.database == "course_db_01"
    assert server.ddl()


def test_the_old_function_names_are_gone():
    functions = importlib.import_module("dbmate.postgresql.functions")

    for removed in [
        "create_postgresql_db",
        "grand_rights_to_own_public_schema",
        "new_postgresql_db_names",
        "init_postgresql_with_demo_user",
        "create_postgresql_readonly_user_for_demo_db",
    ]:
        assert not hasattr(functions, removed), removed
