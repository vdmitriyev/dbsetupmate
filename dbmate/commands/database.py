"""Project group commands of the CLI interface."""

from contextlib import contextmanager
from typing import Iterator, Optional

import typer
from rich.text import Text

from dbmate.configs import cprint, settings
from dbmate.exceptions import DBMateException
from dbmate.postgresql.configs import PostgreSQLConfig
from dbmate.postgresql.manager import PostgresMate

app = typer.Typer(help="Manage database.")


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


@app.command("create-user-readonly")
def create_user_readonly(
    user_name: Optional[str] = typer.Option(
        None,
        "--user-name",
        help="Role to create. Defaults to POSTGRESQL_SHARED_USER_READONLY.",
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        help="Password for the role. Defaults to POSTGRESQL_SHARED_USER_READONLY_PASSWORD.",
    ),
) -> None:
    """Create a user with read-only access to the shared database."""

    with _reporting():
        created_user = _mate().create_user_readonly(user_name=user_name, password=password)

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


@app.command("show-next-db-name")
def show_next_db_name() -> None:
    """Show the next free auto-generated database name."""

    with _reporting():
        names = _mate().show_next_db_name()

    cprint("Next database:", Text(names.database, style="bold blue"))
