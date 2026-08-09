"""Tests for the exception hierarchy and the SQLSTATE mapping."""

import pytest
from psycopg2 import errorcodes

from dbmate.exceptions import (
    DatabaseAlreadyExistsException,
    DatabaseNotExistsException,
    DBConnectionException,
    DBMateException,
    DBOperationException,
    DBUserAlreadyExistsException,
    DBUserNotExistsException,
    InsufficientPrivilegeException,
    exception_for_pgcode,
)
from dbmate.postgresql.connection import translate_error
from tests.fakes import FakeError


@pytest.mark.parametrize(
    ("pgcode", "expected"),
    [
        (errorcodes.DUPLICATE_OBJECT, DBUserAlreadyExistsException),
        (errorcodes.UNDEFINED_OBJECT, DBUserNotExistsException),
        (errorcodes.DUPLICATE_DATABASE, DatabaseAlreadyExistsException),
        (errorcodes.INVALID_CATALOG_NAME, DatabaseNotExistsException),
        (errorcodes.INSUFFICIENT_PRIVILEGE, InsufficientPrivilegeException),
        (errorcodes.INVALID_PASSWORD, DBConnectionException),
        (errorcodes.INVALID_AUTHORIZATION_SPECIFICATION, DBConnectionException),
    ],
)
def test_known_sqlstates_map_to_specific_exceptions(pgcode, expected):
    assert exception_for_pgcode(pgcode) is expected


def test_a_missing_sqlstate_means_the_server_was_never_reached():
    assert exception_for_pgcode(None) is DBConnectionException


def test_an_unknown_sqlstate_falls_back_to_the_generic_error():
    assert exception_for_pgcode("XX000") is DBOperationException


def test_every_exception_derives_from_the_base():
    for pgcode in [errorcodes.DUPLICATE_DATABASE, "XX000", None]:
        assert issubclass(exception_for_pgcode(pgcode), DBMateException)


def test_translate_error_keeps_the_context_and_the_server_details():
    error = FakeError("boom", pgcode=errorcodes.DUPLICATE_DATABASE, pgerror='database "x" already exists')

    translated = translate_error(error, "Could not create database 'x'")

    assert isinstance(translated, DatabaseAlreadyExistsException)
    assert "Could not create database 'x'" in str(translated)
    assert 'database "x" already exists' in str(translated)
    assert translated.pgcode == errorcodes.DUPLICATE_DATABASE


def test_translate_error_without_a_sqlstate():
    translated = translate_error(FakeError("could not connect to server"), "Could not connect")

    assert isinstance(translated, DBConnectionException)
    assert translated.pgcode is None
