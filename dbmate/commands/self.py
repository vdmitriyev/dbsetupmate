"""Self group commands of the CLI interface."""

import os

import typer
from rich.table import Table
from rich.text import Text

from dbmate.configs import console, cprint
from dbmate.version import package_version

app = typer.Typer(help="Helps with the self-manage of the dbmate CLI.")


@app.command()
def version():
    """Print the current dbmate version"""
    cprint(package_version())
