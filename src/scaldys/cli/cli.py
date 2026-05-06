# -*- coding: utf-8 -*-
# cython: language_level=3

import typer
from typer.core import TyperGroup
from click import Context
from art import text2art

import scaldys.cli.commands.cmd_export as cmd_export
import scaldys.cli.commands.cmd_process as cmd_process
import scaldys.cli.commands.cmd_settings as cmd_settings
from scaldys.__about__ import APP_NAME, PACKAGE_NAME, VERSION
from scaldys.cli.commands.arg_types import ARG_TYPE_LOG_LEVEL, ARG_TYPE_VERBOSE
from scaldys.cli.settings import AppSettings
from scaldys.common.logging import setup_logging


def version_callback(value: bool) -> None:
    """
    Return version information.
    """
    if value:
        typer.echo(f"{APP_NAME} version {VERSION}")
        raise typer.Exit()


class HeaderGroup(TyperGroup):
    def get_help(self, ctx: Context) -> str:
        # Override get_help to prepend the ASCII art
        return text2art(APP_NAME) + "\n" + super().get_help(ctx)


def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
    log_level: ARG_TYPE_LOG_LEVEL = None,
    verbose: ARG_TYPE_VERBOSE = False,
) -> None:
    """
    A CLI to run Scaldys commands.

    Global options (--log, --verbose) must appear before the subcommand name:

        scaldys --log debug export config.yml
        scaldys --verbose process --num-tasks 10
    """
    # --version is eager and handled by version_callback above; no further
    # action is needed when it fires.
    if ctx.invoked_subcommand is None:
        return

    # Resolve the log level: CLI flag takes priority over persisted settings.
    if log_level is None:
        log_level = AppSettings().log_level

    # Single, authoritative call to setup_logging for the entire process.
    # Individual commands must NOT call setup_logging — logging is now owned
    # here at the application level.
    setup_logging(log_level, verbose)


app = typer.Typer(
    help=f"A CLI to run {APP_NAME} in a terminal window.",
    cls=HeaderGroup,
    callback=main,
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
    context_settings={
        "max_content_width": 180,
    },
)

app.command()(cmd_export.export)
app.command()(cmd_process.process)
app.add_typer(cmd_settings.app, name="settings")


if __name__ == "__main__":
    app()
