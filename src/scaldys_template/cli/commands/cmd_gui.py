# -*- coding: utf-8 -*-
# cython: language_level=3

"""
``gui`` CLI command — launch the Tkinter GUI application.

The GUI is always spawned as a detached process so the terminal is freed
immediately.  The command returns as soon as the window is visible.

Invocation examples
--------------------
    scaldys-template gui
    scaldys-template gui --params params.json
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from scaldys_template.__about__ import APP_NAME, PACKAGE_NAME

__all__ = ["gui"]

logger = logging.getLogger(PACKAGE_NAME)

# Environment variable used internally to distinguish the spawned worker
# process from the launcher process, avoiding infinite recursion.
_WORKER_ENV = "_SCALDYS_GUI_WORKER"

ARG_TYPE_PARAMS_FILE = Annotated[
    Path | None,
    typer.Option(
        "--params",
        "-p",
        help="Pre-load a JSON parameter file into the analyzer on startup.",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
]


def gui(
    ctx: typer.Context,
    params_file: ARG_TYPE_PARAMS_FILE = None,
) -> None:
    """
    Launch the Signal Analyzer graphical user interface.

    The GUI opens in a detached process and the terminal is released
    immediately.  Optionally pass [bold]--params[/bold] to pre-load a JSON
    parameter file saved with [italic]File → Save parameters…[/italic].
    """
    # -----------------------------------------------------------------------
    # Worker branch — runs inside the spawned background process.
    # -----------------------------------------------------------------------
    if os.environ.get(_WORKER_ENV) == "1":
        exit_code = 0
        try:
            from scaldys_template.tk.app import Application

            logger.info("Launching %s GUI", APP_NAME)
            app = Application()

            if params_file is not None:

                def _load_on_startup() -> None:
                    from scaldys_template.core.parameter_store import load_parameters

                    try:
                        params = load_parameters(params_file)
                        app.analyzer_frame.set_parameters(params)
                        logger.info("Pre-loaded parameters from %s", params_file)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Could not pre-load parameters from %s: %s", params_file, exc
                        )

                app.after(200, _load_on_startup)

            app.mainloop()
        except Exception:
            logger.critical("GUI application failed to start", exc_info=True)
            exit_code = 1
            raise
        finally:
            # Force-exit so lingering library threads don't block the worker process.
            os._exit(exit_code)

    # -----------------------------------------------------------------------
    # Launcher branch — spawns the worker and returns immediately.
    # -----------------------------------------------------------------------
    if getattr(sys, "frozen", False):
        # In a frozen environment (e.g. PyInstaller), sys.executable is the
        # path to the application binary itself.
        cmd = [sys.executable, "gui"]
    else:
        # In a standard environment, use the Python interpreter to run the
        # package as a module.
        cmd = [sys.executable, "-m", PACKAGE_NAME, "gui"]

    if params_file is not None:
        cmd += ["--params", str(params_file)]

    env = os.environ.copy()
    env[_WORKER_ENV] = "1"

    # If --verbose is passed to the main CLI, don't redirect output so errors are visible.
    verbose = ctx.parent.params.get("verbose", False) if ctx.parent else False

    kwargs: dict = {
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": None if verbose else subprocess.DEVNULL,
        "stderr": None if verbose else subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
        # pythonw.exe suppresses the brief console flash on Windows.
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if pythonw.exists():
            cmd[0] = str(pythonw)
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(cmd, **kwargs)  # noqa: S603
    logger.info("Launched %s GUI", APP_NAME)
