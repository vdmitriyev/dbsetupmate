"""Project group commands of the CLI interface."""

import typer

app = typer.Typer(help="Manage database.")

from dbmate.postgresql.functions import create_postgresql_db


@app.command()
def create(
    new_db_name: str = typer.Option(
        None,
        "--new-db-name",
        help="Database name",
    ),
    new_db_user: str = typer.Option(
        None,
        "--new-db-user",
        help="Database user",
    ),
    new_db_password: str = typer.Option(
        None,
        "--new-db-password",
        help="Database passowrd",
    ),
) -> None:
    """Create a a new database"""
    create_postgresql_db(new_db_name, new_db_user, new_db_password)
