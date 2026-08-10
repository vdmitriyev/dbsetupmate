"""Self group commands of the CLI interface."""

import typer

from dbsetupmate.configs import cprint
from dbsetupmate.version import package_version

app = typer.Typer(help="Helps with the self-manage of the dbsetupmate CLI.")


@app.command()
def version():
    """Print the current dbsetupmate version"""
    cprint(package_version())
