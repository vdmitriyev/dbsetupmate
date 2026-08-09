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


@app.command()
def create(
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
    skip_demo_access: bool = typer.Option(
        False,
        "--skip-demo-access",
        help="Do not grant the new user read-only access to the demo database.",
    ),
) -> None:
    """Create a new database together with its owner and login user."""

    mate = _mate()

    with _reporting():
        if not new_db_name or not new_db_user:
            names = mate.next_database_names()
            new_db_name = new_db_name or names.database
            new_db_user = new_db_user or names.user
            cprint("Generated names:", Text(f"{new_db_name} / {new_db_user}", style="bold blue"))

        created = mate.create_database(
            db_name=new_db_name,
            db_user=new_db_user,
            db_password=new_db_password,
            grant_demo_access=not skip_demo_access,
        )

    if created.dry_run:
        cprint(Text("✓", style="bold green"), f"Dry run: database '{created.database}' was not created")
        return

    cprint(
        Text("✓", style="bold green"),
        f"Database '{created.database}' was created for user '{created.login_role}'"
        + (" with demo access" if created.granted_demo_access else ""),
    )


@app.command("init-demo")
def init_demo() -> None:
    """Create the shared demo database and harden its public schema."""

    with _reporting():
        created = _mate().init_demo_database()

    cprint(Text("✓", style="bold green"), f"Demo database '{created.database}' is ready")


@app.command("create-readonly-user")
def create_readonly_user(
    user_name: Optional[str] = typer.Option(
        None,
        "--user-name",
        help="Role to create. Defaults to POSTGRESQL_DEMO_USER_READONLY.",
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        help="Password for the role. Defaults to POSTGRESQL_DEMO_USER_READONLY_PASSWORD.",
    ),
) -> None:
    """Create a user with read-only access to the demo database."""

    with _reporting():
        created_user = _mate().create_readonly_user(user_name=user_name, password=password)

    cprint(Text("✓", style="bold green"), f"Read-only user '{created_user}' is ready")


@app.command("next-names")
def next_names() -> None:
    """Show the next free auto-generated database and user names."""

    with _reporting():
        names = _mate().next_database_names()

    cprint("Next database:", Text(names.database, style="bold blue"))
    cprint("Next user:", Text(names.user, style="bold blue"))
