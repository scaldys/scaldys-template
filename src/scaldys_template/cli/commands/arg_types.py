

from typing import Annotated

import typer

__all__ = ["ARG_TYPE_LOG_LEVEL", "ARG_TYPE_VERBOSE"]


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
    str | None,
    typer.Option(
        "--log", "-l", help="Set the log level (off, debug, info, warning, error, critical)"
    ),
]
