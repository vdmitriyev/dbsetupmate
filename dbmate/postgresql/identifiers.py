"""Validation and normalisation of PostgreSQL identifiers.

All SQL in this package is built with :mod:`psycopg2.sql`, which renders every
identifier double quoted. PostgreSQL folds *unquoted* identifiers to lower case,
so quoting is only equivalent to the historic behaviour once a name has been
normalised to the lower case subset - which is what this module does.
"""

import re

from dbmate.configs import logger
from dbmate.constants import MAX_IDENTIFIER_BYTES
from dbmate.exceptions import InvalidIdentifierException

#: Names that survive quoting unchanged and stay pleasant to administer.
IDENTIFIER_PATTERN = re.compile(r"^[a-z_][a-z0-9_$]*$")


def normalize_identifier(name: str, kind: str = "identifier") -> str:
    """Validates a database or role name and returns its canonical form.

    Args:
        name (str): the raw name, e.g. as typed on the command line
        kind (str): what the name refers to, used in error messages ("database", "role", ...)

    Returns:
        str: the name, stripped and lower cased

    Raises:
        InvalidIdentifierException: if the name is empty, too long, or contains
            characters outside ``[a-z0-9_$]`` after normalisation
    """

    if not isinstance(name, str):
        raise InvalidIdentifierException(f"A {kind} name must be a string, got {type(name).__name__}")

    stripped = name.strip()
    if not stripped:
        raise InvalidIdentifierException(f"A {kind} name must not be empty")

    normalized = stripped.lower()
    if normalized != stripped:
        # PostgreSQL would have folded an unquoted name the same way.
        logger.warning("The %s name %r was lower cased to %r", kind, stripped, normalized)

    if len(normalized.encode("utf-8")) > MAX_IDENTIFIER_BYTES:
        raise InvalidIdentifierException(
            f"The {kind} name {normalized!r} is longer than {MAX_IDENTIFIER_BYTES} bytes; "
            "PostgreSQL would truncate it silently"
        )

    if not IDENTIFIER_PATTERN.match(normalized):
        raise InvalidIdentifierException(
            f"The {kind} name {normalized!r} is not a valid identifier; "
            "it must start with a letter or underscore and contain only letters, digits, '_' or '$'"
        )

    return normalized
