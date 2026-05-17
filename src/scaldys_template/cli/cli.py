# -*- coding: utf-8 -*-
# cython: language_level=3

import typer
from typer.core import TyperGroup
from click import Context
from art import text2art
from rich.console import Console

import scaldys_template.cli.commands.cmd_export as cmd_export
import scaldys_template.cli.commands.cmd_process as cmd_process
import scaldys_template.cli.commands.cmd_settings as cmd_settings
from scaldys_template.__about__ import APP_NAME, VERSION
from scaldys_template.cli.commands.arg_types import ARG_TYPE_LOG_LEVEL, ARG_TYPE_VERBOSE
from scaldys_template.cli.settings import AppSettings
from scaldys_template.common.logging import setup_logging

console = Console()


def version_callback(value: bool) -> None:
    """
    Return version information.
    """
    if value:
        console.print(f"[bold]{APP_NAME}[/bold] version [cyan]{VERSION}[/cyan]")
        raise typer.Exit()


class HeaderGroup(TyperGroup):
    def format_help(self, ctx: Context, formatter) -> None:
        # With rich_markup_mode="rich", Typer bypasses the formatter and renders
        # options/commands via Rich directly, so formatter.write() ends up after the
        # panels. Instead, print the art straight to the console before the parent
        # renders its Rich content.
        console.print(text2art(APP_NAME))
        super().format_help(ctx, formatter)


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
    rich_markup_mode="rich",
    context_settings={
        "max_content_width": 180,
    },
)

app.command()(cmd_export.export)
app.command()(cmd_process.process)
app.add_typer(cmd_settings.app, name="settings")


if __name__ == "__main__":
    app()
