"""Project group commands of the CLI interface."""

from contextlib import contextmanager
from dataclasses import fields
from typing import Iterator, Optional

import typer
from rich.table import Table
from rich.text import Text

from dbmate.configs import console, cprint, settings
from dbmate.exceptions import DBMateException
from dbmate.postgresql.configs import PostgreSQLConfig
from dbmate.postgresql.manager import PostgresMate

app = typer.Typer(help="Manage database.")

#: What a secret reads as in `show-config`.
MASKED = "***"


def _mate() -> PostgresMate:
    """Builds a manager from the environment loaded by the root callback."""

    return PostgresMate(PostgreSQLConfig.from_env(), dry_run=settings.dry_run)


@contextmanager
def _reporting() -> Iterator[None]:
    """Turns a dbmate failure into a red message and a non-zero exit code."""

    try:
        yield
    except DBMateException as ex:
        cprint(Text("✖", style="bold red"), f"{ex}", style="red", log_level="error")
        raise typer.Exit(code=1) from ex


def _confirm(message: str) -> None:
    """Gates a destructive command. A dry run needs no gate: it changes nothing."""

    if settings.dry_run:
        return

    typer.confirm(message, abort=True)


@app.command("create-db")
def create_db(
    new_db_name: Optional[str] = typer.Option(
        None,
        "--new-db-name",
        help="Database name. Generated from the configured prefix when omitted.",
    ),
    new_db_user: Optional[str] = typer.Option(
        None,
        "--new-db-user",
        help="Database user. Generated from the configured prefix when omitted.",
    ),
    new_db_password: str = typer.Option(
        ...,
        "--new-db-password",
        help="Password for the new database user.",
        prompt=True,
        hide_input=True,
    ),
) -> None:
    """Create a new database together with its owner and login user."""

    mate = _mate()

    with _reporting():
        if not new_db_name or not new_db_user:
            names = mate.show_next_db_name()
            new_db_name = new_db_name or names.database
            new_db_user = new_db_user or names.user
            cprint("Generated names:", Text(f"{new_db_name} / {new_db_user}", style="bold blue"))

        created = mate.create_db(
            db_name=new_db_name,
            db_user=new_db_user,
            db_password=new_db_password,
        )

    if created.dry_run:
        cprint(Text("✓", style="bold green"), f"Dry run: database '{created.database}' was not created")
        return

    cprint(
        Text("✓", style="bold green"),
        f"Database '{created.database}' was created for user '{created.login_role}'",
    )


@app.command("create-shared-db")
def create_shared_db() -> None:
    """Create the shared database and harden its public schema."""

    with _reporting():
        created = _mate().create_shared_db()

    cprint(Text("✓", style="bold green"), f"Shared database '{created.database}' is ready")


@app.command("create-shared-user-readonly")
def create_shared_user_readonly(
    user_name: Optional[str] = typer.Option(
        None,
        "--user-name",
        help="Role to create. Defaults to POSTGRESQL_SHARED_USER_READONLY.",
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        help=(
            "Password for the role. Defaults to POSTGRESQL_SHARED_USER_READONLY_PASSWORD. "
            "A password given here ends up in the shell history; prefer the environment."
        ),
    ),
) -> None:
    """Create a login role and grant it read-only access to the shared database."""

    with _reporting():
        created_user = _mate().create_shared_user_readonly(user_name=user_name, password=password)

    cprint(Text("✓", style="bold green"), f"Read-only user '{created_user}' is ready")


@app.command("grant-shared-access")
def grant_shared_access(
    user_name: str = typer.Option(
        ...,
        "--user-name",
        help="Role to grant read-only access to the shared database.",
    ),
) -> None:
    """Grant an existing user read-only access to the shared database."""

    with _reporting():
        _mate().grant_shared_access(user_name)

    cprint(Text("✓", style="bold green"), f"Granted '{user_name}' read-only access to the shared database")


@app.command("revoke-shared-access")
def revoke_shared_access(
    user_name: str = typer.Option(
        ...,
        "--user-name",
        help="Role to revoke read-only access to the shared database from.",
    ),
) -> None:
    """Revoke a user's read-only access to the shared database. The role itself is kept."""

    with _reporting():
        _mate().revoke_shared_access(user_name)

    cprint(Text("✓", style="bold green"), f"Revoked '{user_name}' read-only access to the shared database")


@app.command("set-user-password")
def set_user_password(
    user_name: str = typer.Option(
        ...,
        "--user-name",
        help="Role whose password is replaced.",
    ),
    password: str = typer.Option(
        ...,
        "--password",
        help="The new password.",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
    ),
) -> None:
    """Replace the password of an existing user."""

    with _reporting():
        changed_user = _mate().set_user_password(user_name, password)

    cprint(Text("✓", style="bold green"), f"The password of '{changed_user}' was changed")


@app.command("drop-db")
def drop_db(
    db_name: str = typer.Option(
        ...,
        "--db-name",
        help="Database to drop. The group role of the same name goes with it.",
    ),
    db_user: Optional[str] = typer.Option(
        None,
        "--db-user",
        help="Login role to drop as well. It cannot be derived from the database name.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt.",
    ),
) -> None:
    """Drop a database, its owning group role and, when named, its login user."""

    if not yes:
        _confirm(f"Drop the database '{db_name}' and its roles? This cannot be undone.")

    with _reporting():
        _mate().drop_db(db_name, db_user)

    if settings.dry_run:
        cprint(Text("✓", style="bold green"), f"Dry run: database '{db_name}' was not dropped")
        return

    cprint(Text("✓", style="bold green"), f"Database '{db_name}' was dropped")


@app.command("drop-user")
def drop_user(
    user_name: str = typer.Option(
        ...,
        "--user-name",
        help="Role to drop. It must not own any object left on the server.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt.",
    ),
) -> None:
    """Drop a user."""

    if not yes:
        _confirm(f"Drop the role '{user_name}'? This cannot be undone.")

    with _reporting():
        _mate().drop_user(user_name)

    if settings.dry_run:
        cprint(Text("✓", style="bold green"), f"Dry run: role '{user_name}' was not dropped")
        return

    cprint(Text("✓", style="bold green"), f"Role '{user_name}' was dropped")


@app.command("show-next-db-name")
def show_next_db_name() -> None:
    """Show the next free auto-generated database name."""

    with _reporting():
        names = _mate().show_next_db_name()

    cprint("Next database:", Text(names.database, style="bold blue"))


@app.command("show-dbs")
def show_dbs() -> None:
    """Show the databases built from the configured prefix, with their owners."""

    with _reporting():
        databases = _mate().list_dbs()

    if not databases:
        cprint("No database matches the configured prefix.")
        return

    table = Table(box=None, pad_edge=False)
    table.add_column("Database", style="bold blue")
    table.add_column("Owner")
    for item in databases:
        table.add_row(item.database, item.owner)

    console.print(table)


@app.command("show-users")
def show_users() -> None:
    """Show the roles built from the configured user prefix."""

    with _reporting():
        users = _mate().list_users()

    if not users:
        cprint("No role matches the configured prefix.")
        return

    for name in users:
        cprint(Text(name, style="bold blue"))


@app.command("show-config")
def show_config() -> None:
    """Show the resolved PostgreSQL settings, with every password masked."""

    with _reporting():
        config = PostgreSQLConfig.from_env()

    table = Table(box=None, pad_edge=False)
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    for item in fields(config):
        value = getattr(config, item.name)
        # The secrets are exactly the fields PostgreSQLConfig marks `repr=False`,
        # so a password added there later is masked here without touching this code.
        if not item.repr:
            value = MASKED if value else "(not set)"
        table.add_row(item.name, str(value))

    console.print(table)
