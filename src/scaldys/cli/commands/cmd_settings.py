# -*- coding: utf-8 -*-
# cython: language_level=3

import logging

import typer
from typing_extensions import Annotated

from scaldys.__about__ import APP_NAME, PACKAGE_NAME
from scaldys.cli.settings import AppSettings

__all__ = ["log"]


logger = logging.getLogger(PACKAGE_NAME)

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
        typer.echo(f"{APP_NAME} log level: '{settings.log_level}'")


@app.command()
def log(level: ARG_TYPE_LOG_LEVEL) -> None:
    """
    Update and persist the logging level for the application.

    This function allows the user to set the desired log level for the application. The new logging
    level is saved to the application's settings and remains active across sessions.
    """

    settings = AppSettings()
    settings.log_level = level
    settings.save()

    return None
