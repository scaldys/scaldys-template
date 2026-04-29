# -*- coding: utf-8 -*-
# cython: language_level=3

import typer
from typer.core import TyperGroup
from click import Context
from art import text2art, tprint

import scaldys.cli.commands.cmd_export as cmd_export
import scaldys.cli.commands.cmd_settings as cmd_settings
from scaldys.__about__ import APP_NAME, VERSION


def version_callback(value: bool):
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
    version: bool = typer.Option(None, "--version", callback=version_callback),
):
    """
    Show the app's version number and exit.
    """
    pass


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
app.add_typer(cmd_settings.app, name="settings")


if __name__ == "__main__":
    app()
