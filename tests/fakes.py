"""An in-memory stand-in for a PostgreSQL server.

The fake records every statement dbmate sends, so tests can assert on the SQL
that was built and on the parameters it was sent with - without a live database.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import psycopg2
from psycopg2 import sql


class FakeError(psycopg2.Error):
    """A driver error with a controllable SQLSTATE.

    ``psycopg2.Error.pgcode`` is read-only, so it is shadowed by a property here.
    """

    def __init__(self, message: str, pgcode: Optional[str] = None, pgerror: Optional[str] = None) -> None:
        super().__init__(message)
        self._pgcode = pgcode
        self._pgerror = pgerror or message

    @property
    def pgcode(self) -> Optional[str]:
        return self._pgcode

    @property
    def pgerror(self) -> Optional[str]:
        return self._pgerror


@dataclass
class Executed:
    """One statement as the fake server saw it."""

    text: str
    statement: Any
    params: Optional[Sequence]
    database: str
    user: str


def statement_text(statement: Any) -> str:
    """Renders a statement for matching and assertions, without a connection.

    ``psycopg2.sql`` objects can only be rendered as real SQL through a live
    connection, so their ``repr`` is used instead - it is deterministic and it
    still shows every identifier and every ``%s`` placeholder.
    """

    if isinstance(statement, str):
        return statement
    if isinstance(statement, sql.Composable):
        return repr(statement)

    return str(statement)


class FakeCursor:
    """Records statements and serves rows decided by the fake server."""

    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection
        self.closed = False
        self._rows: List[Tuple] = []

    def execute(self, statement, params=None) -> None:
        text = statement_text(statement)
        server = self.connection.server
        server.executed.append(
            Executed(
                text=text,
                statement=statement,
                params=params,
                database=self.connection.database,
                user=self.connection.user,
            )
        )
        error = server.error_for(text)
        if error is not None:
            raise error
        self._rows = server.rows_for(text, params)

    def fetchone(self) -> Optional[Tuple]:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> List[Tuple]:
        return list(self._rows)

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    """Records transaction handling and hands out cursors."""

    def __init__(self, server: "FakeServer", database: str, user: str) -> None:
        self.server = server
        self.database = database
        self.user = user
        self.autocommit = False
        self.closed = False
        self.commits = 0
        self.rollbacks = 0
        self.cursors: List[FakeCursor] = []

    def cursor(self) -> FakeCursor:
        cursor = FakeCursor(self)
        self.cursors.append(cursor)

        return cursor

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


@dataclass
class FakeServer:
    """State and behaviour of the stand-in server.

    Attributes:
        databases: database names the server reports as existing
        roles: role names the server reports as existing
        database_owners: database name -> owning role, defaulting to ``admin``
        statement_errors: substring of a statement -> error raised for it
        connect_errors: database name -> error raised instead of connecting
        executed: every statement received, in order
        connections: every connection opened, in order
    """

    databases: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    database_owners: Dict[str, str] = field(default_factory=dict)
    statement_errors: Dict[str, psycopg2.Error] = field(default_factory=dict)
    connect_errors: Dict[str, psycopg2.Error] = field(default_factory=dict)
    executed: List[Executed] = field(default_factory=list)
    connections: List[FakeConnection] = field(default_factory=list)

    def connect(self, **kwargs) -> FakeConnection:
        database = kwargs["dbname"]
        error = self.connect_errors.get(database)
        if error is not None:
            raise error
        connection = FakeConnection(self, database=database, user=kwargs["user"])
        self.connections.append(connection)

        return connection

    def error_for(self, text: str) -> Optional[psycopg2.Error]:
        for needle, error in self.statement_errors.items():
            if needle in text:
                return error

        return None

    def rows_for(self, text: str, params) -> List[Tuple]:
        if "FROM pg_database WHERE datname = " in text:
            return [(1,)] if params[0] in self.databases else []
        if "FROM pg_roles WHERE rolname = " in text:
            return [(1,)] if params[0] in self.roles else []
        if "SELECT datname FROM pg_database WHERE left(" in text:
            return [(name,) for name in self.databases if name.startswith(params["prefix"])]
        if "pg_get_userbyid(datdba)" in text:
            return [
                (name, self.database_owners.get(name, "admin"))
                for name in sorted(self.databases)
                if name.startswith(params["prefix"])
            ]
        if "SELECT rolname FROM pg_roles WHERE left(" in text:
            return [(name,) for name in sorted(self.roles) if name.startswith(params["prefix"])]

        return []

    # -- assertion helpers -------------------------------------------------

    def texts(self) -> List[str]:
        """Every statement, in the order it was sent."""

        return [item.text for item in self.executed]

    def ddl(self) -> List[Executed]:
        """Only the statements that change the server."""

        return [item for item in self.executed if not item.text.lstrip().upper().startswith("SELECT")]

    def ddl_texts(self) -> List[str]:
        return [item.text for item in self.ddl()]
