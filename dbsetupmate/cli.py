"""Root command line interface of dbsetupmate."""

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.table import Table
from rich.text import Text
from typing_extensions import Annotated

from dbsetupmate.commands import postgresql as postgresql_module
from dbsetupmate.commands import self as self_module
from dbsetupmate.configs import console, cprint, settings
from dbsetupmate.logger import configure_logging
from dbsetupmate.version import package_summary, package_version

app = typer.Typer(
    help=(
        "`dbsetupmate` overtakes a role of a database mate, "
        "whose purpose is to create and maintain database schemas and users"
    )
)


app.add_typer(postgresql_module.app, name="postgresql")
app.add_typer(postgresql_module.app, name="pg", hidden=True)
app.add_typer(self_module.app, name="self")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    env_file: Annotated[
        Path,
        typer.Option(
            "--env-file",
            "-e",
            help="Specify a path to a .env file to load environment variables.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Simulate execution without making changes.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose outputs.",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show version.",
        ),
    ] = False,
) -> None:
    """
    This function runs *before* any other command (subcommand)
    or when the app is called without a subcommand.
    """
    settings.dry_run = dry_run
    settings.verbose = verbose

    # Load the environment before anything reads it: `PostgreSQLConfig.from_env()`
    # is called inside the subcommands, which run after this callback returns.
    if env_file:
        cprint(
            "Loading environment variables from:",
            Text(f"{env_file}", style="bold blue"),
        )
        success = load_dotenv(env_file, override=True)
        if not success:
            typer.echo(f"Warning: Could not load variables from {env_file}", err=True)
    else:
        load_dotenv()

    # The library only ever attaches a NullHandler; the CLI opts into file logging.
    configure_logging()

    if settings.verbose:
        cprint(
            Text("✅", style="bold green"),
            "Verbose mode:",
            Text("enabled", style="bold green"),
        )
        cprint(
            Text("✅", style="bold green"),
            "Dry run mode:",
            Text(
                f"{settings.dry_run}",
                style=f'bold {"red" if not settings.dry_run else "green"}',
            ),
        )
    elif settings.dry_run:
        cprint(
            Text("✅", style="bold green"),
            "Dry run mode:",
            Text("enabled", style="bold green"),
        )

    if version:
        if settings.verbose:
            table = Table()
            table.add_column("Field", justify="right", style="cyan", no_wrap=True)
            table.add_column("Value", justify="left", style="yellow", no_wrap=True)
            summary = package_summary()
            for item in summary:
                table.add_row(item["field"], item["value"])
            console.print(table)
        else:
            cprint(f"{package_version()}", style="yellow")
        raise typer.Exit(code=0)

    # If a subcommand was provided, don't exit; continue to the subcommand.
    # Otherwise, Typer will handle exiting or showing the help page.
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
