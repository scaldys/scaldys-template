# cython: language_level=3

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from scaldys_template.__about__ import APP_NAME, PACKAGE_NAME, VERSION
from scaldys_template.common.app_location import AppLocation
from scaldys_template.core.export import export_data

__all__ = ["export"]


logger = logging.getLogger(PACKAGE_NAME)
console = Console()
err_console = Console(stderr=True)

# Type definitions for fixed and optional arguments, specific to this command
ARG_TYPE_CONFIG_PATH = Annotated[Path, typer.Argument()]

ARG_TYPE_OUTPUT_PATH = Annotated[Path | None, typer.Argument()]

ARG_TYPE_NUM_VALUES = Annotated[
    int,
    typer.Option(
        "--num_values", "-n", help="Only export the first 'num_values' items (if num_values > 0)."
    ),
]

ARG_TYPE_FORCE = Annotated[
    bool,
    typer.Option(
        "--force",
        "-f",
        help="Overwrite the output file if it already exists.",
    ),
]


def export(
    ctx: typer.Context,
    config_file: ARG_TYPE_CONFIG_PATH = Path("config.yml"),
    output_dir: ARG_TYPE_OUTPUT_PATH = None,
    num_values: ARG_TYPE_NUM_VALUES = 0,
    force: ARG_TYPE_FORCE = False,
) -> None:
    """
    Export data according to specifications in a configuration file.

    This command reads a configuration file and exports data to a specified directory.
    It can limit the number of values exported and overwrite existing files if required.
    """
    # Resolved here rather than in the default argument to avoid a module-import-time
    # side effect: default expressions are evaluated once at definition time, which would
    # call AppLocation.get_directory() (and its logger.debug()) before logging is configured.
    if output_dir is None:
        output_dir = AppLocation.get_directory(AppLocation.AppDataDir).joinpath("data_export")

    logger.info(f"Starting {APP_NAME} version {VERSION}")
    logger.debug(f"Current working directory : {Path.cwd()}")
    logger.debug(f"Current log level : {logger.getEffectiveLevel()}")

    if output_dir.exists():
        if not force:
            logger.error(
                f"The output directory already exists, use the '--force' option to overwrite"
                f" : {output_dir.resolve()!s}."
            )
            err_console.print(
                Panel(
                    f"Output directory already exists:\n[cyan]{output_dir.resolve()}[/cyan]\n\n"
                    f"Use [bold]--force[/bold] to overwrite.",
                    title="[bold red]Error[/bold red]",
                    border_style="red",
                    expand=False,
                )
            )
            return
        else:
            logger.info(
                f"The output directory already exists. Files with the same name will be"
                f" overwritten (option '--force' used) : {output_dir.resolve()!s}."
            )
            console.print(
                f"[yellow]Output directory exists — overwriting (--force)[/yellow]:"
                f" [cyan]{output_dir.resolve()}[/cyan]"
            )

    logger.info(f"Configuration file: {config_file}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Number of values: {num_values}")

    console.print(
        f"Exporting data from [cyan]{config_file}[/cyan]"
        f" to [cyan]{output_dir}[/cyan]"
        + (f" ([bold]{num_values}[/bold] values)" if num_values > 0 else "")
        + "..."
    )

    export_data(
        config_file,
        output_dir,
        num_values,
    )

    console.print("[green]Export complete.[/green]")
    logger.info(f"{APP_NAME} stopped")
