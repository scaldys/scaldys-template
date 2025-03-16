# -*- coding: utf-8 -*-
# cython: language_level=3

import logging
import os
from datetime import datetime, timedelta, date, time
from pathlib import Path

import typer
from typing_extensions import Annotated

from scaldys.__about__ import APP_NAME, PACKAGE_NAME, VERSION
from scaldys.core.export import export_data
from scaldys.common.app_location import AppLocation
from scaldys.cli.commands.arg_types import ARG_TYPE_VERBOSE, ARG_TYPE_LOG_LEVEL
from scaldys.cli.settings import AppSettings
from scaldys.common.app_logging import setup_logging

__all__ = ["export"]


logger = logging.getLogger(PACKAGE_NAME)

next_day = datetime.combine(date.today() + timedelta(days=1), time(0))

# Type definitions for fixed and optional arguments, specific to this command
ARG_TYPE_CONFIG_PATH = Annotated[Path, typer.Argument()]

ARG_TYPE_OUTPUT_PATH = Annotated[Path, typer.Argument()]

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


def first_last_callback(value: str):
    if value in ["10sec", "1min", "1hour", "1day"]:
        return value


def export(
    ctx: typer.Context,
    config_file: ARG_TYPE_CONFIG_PATH = Path("config.yml"),
    output_dir: ARG_TYPE_OUTPUT_PATH = AppLocation.get_directory(AppLocation.AppDataDir).joinpath(
        "data_export"
    ),
    num_values: ARG_TYPE_NUM_VALUES = 0,
    force: ARG_TYPE_FORCE = False,
    verbose: ARG_TYPE_VERBOSE = False,
    log_level: ARG_TYPE_LOG_LEVEL = None,
) -> None:
    """
    Export data according to specifications in a configuration file.

    This command reads a configuration file and exports data to a specified directory.
    It can limit the number of values exported and overwrite existing files if required.
    """
    app_settings = AppSettings()
    if log_level is None:
        log_level = app_settings.log_level

    setup_logging(log_level, verbose)

    logger.info(f"Starting {APP_NAME} version {VERSION}")
    logger.debug(f"Current working directory : {os.getcwd()}")
    logger.debug(f"Current log level : {logger.getEffectiveLevel()}")

    if output_dir.exists():
        message = "The output directory already exists"
        if not force:
            logger.error(
                f"{message}, use the '--force' option to overwrite : {str(output_dir.resolve())}."
            )
            return
        else:
            logger.info(
                f"{message}. Files with the same name will be overwritten (option '--force' used) : {str(output_dir.resolve())}."
            )

    num_values += 10

    logger.info(f"Configuration file: {config_file}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Number of values: {num_values}")

    export_data(
        config_file,
        output_dir,
        num_values,
    )

    logger.info(f"{APP_NAME} stopped")
