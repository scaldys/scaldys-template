import logging
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from scaldys_template.__about__ import APP_NAME, PACKAGE_NAME
from scaldys_template.cli.settings import AppSettings

__all__ = ["log"]


logger = logging.getLogger(PACKAGE_NAME)
console = Console()
err_console = Console(stderr=True)

app = typer.Typer()

# Type definitions for fixed and optional arguments, specific to this command
ARG_TYPE_LOG_LEVEL = Annotated[
    str,
    typer.Argument(
        help="Must be a valid logging level string: 'off', 'debug', 'info', 'warning', 'error', or 'critical'."
    ),
]


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Entry point for managing application settings.

    This command allows users to view or interact with application settings.
    When invoked without a subcommand, it displays the current logging level of the application.
    """
    if ctx.invoked_subcommand is None:
        settings = AppSettings()
        console.print(
            Panel(
                f"Log level: [cyan]{settings.log_level}[/cyan]",
                title=f"[bold]{APP_NAME} Settings[/bold]",
                expand=False,
            )
        )


@app.command()
def log(level: ARG_TYPE_LOG_LEVEL) -> None:
    """
    Update and persist the logging level for the application.

    This function allows the user to set the desired log level for the application. The new logging
    level is saved to the application's settings and remains active across sessions.
    """

    settings = AppSettings()
    try:
        settings.log_level = level
    except ValidationError:
        valid = "off, debug, info, warning, error, critical"
        err_console.print(
            f"[bold red]Error:[/bold red] '[cyan]{level}[/cyan]' is not a valid log level.\n"
            f"Valid choices are: [cyan]{valid}[/cyan]"
        )
        raise typer.Exit(code=1) from None
    settings.save()
    console.print(f"Log level set to [cyan]{level}[/cyan]")
