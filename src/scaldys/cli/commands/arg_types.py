# -*- coding: utf-8 -*-
# cython: language_level=3

import typer

from typing_extensions import Annotated
from typing import Optional

__all__ = ["ARG_TYPE_VERBOSE", "ARG_TYPE_LOG_LEVEL"]


# Type definitions for fixed and optional arguments, common to multiple commands
ARG_TYPE_VERBOSE = Annotated[
    bool,
    typer.Option(
        "--verbose",
        "-v",
        help="Enable verbose mode: show logging output on standard output.",
    ),
]


ARG_TYPE_LOG_LEVEL = Annotated[
    Optional[str],
    typer.Option("--log", "-l", help="Set the log level (off, debug, info, warn, error, critical)"),
]
