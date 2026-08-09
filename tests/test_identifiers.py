"""Tests for identifier validation."""

import pytest

from dbmate.exceptions import InvalidIdentifierException
from dbmate.postgresql.identifiers import normalize_identifier


def test_accepts_a_plain_name():
    assert normalize_identifier("dbmate_db_01") == "dbmate_db_01"


def test_strips_surrounding_whitespace():
    assert normalize_identifier("  dbmate_db_01\n") == "dbmate_db_01"


def test_lower_cases_like_postgresql_would():
    # PostgreSQL folds unquoted identifiers to lower case; quoting must not change that.
    assert normalize_identifier("MyDB") == "mydb"


@pytest.mark.parametrize("name", ["", "   ", "\t"])
def test_rejects_an_empty_name(name):
    with pytest.raises(InvalidIdentifierException, match="must not be empty"):
        normalize_identifier(name)


@pytest.mark.parametrize("name", ["1st_db", "my-db", "my db", 'drop"me', "db;drop", "sch.ema", "100%"])
def test_rejects_names_that_are_not_identifiers(name):
    with pytest.raises(InvalidIdentifierException, match="not a valid identifier"):
        normalize_identifier(name)


def test_rejects_names_postgresql_would_truncate():
    with pytest.raises(InvalidIdentifierException, match="longer than 63 bytes"):
        normalize_identifier("d" * 64)


def test_accepts_a_name_at_the_length_limit():
    assert normalize_identifier("d" * 63) == "d" * 63


def test_rejects_a_non_string():
    with pytest.raises(InvalidIdentifierException, match="must be a string"):
        normalize_identifier(None)


def test_names_the_kind_in_the_error():
    with pytest.raises(InvalidIdentifierException, match="role name"):
        normalize_identifier("no good", "role")
