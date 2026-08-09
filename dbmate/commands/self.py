"""Self group commands of the CLI interface."""

import typer

from dbmate.configs import cprint
from dbmate.version import package_version

app = typer.Typer(help="Helps with the self-manage of the dbmate CLI.")


@app.command()
def version():
    """Print the current dbmate version"""
    cprint(package_version())
