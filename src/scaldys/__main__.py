# -*- coding: utf-8 -*-
# cython: language_level=3

"""
Application entry point — lifecycle management.

This module is the single entry point for all execution paths:
  - Installed CLI:      `scaldys` (via pyproject.toml scripts entry point)
  - Module execution:   `python -m scaldys`
  - Frozen executable:  PyInstaller-built binary

Its responsibilities are strictly lifecycle concerns that must be in place
*before* the CLI argument parser runs and *before* any subcommand executes:

  1. multiprocessing.freeze_support()   — mandatory first line for PyInstaller + multiprocessing
  2. _pre_init_logging()               — CRITICAL-only stderr fallback so startup errors are visible
  3. _setup_crash_hook()               — clean handling of unhandled exceptions (log + exit 1)
  4. _setup_signal_handlers()          — SIGINT/SIGTERM → set _shutdown_event + clean exit
  5. _setup_asyncio_policy()           — correct event loop policy on Windows for async I/O
  6. _validate_environment()           — fail fast if the runtime environment is unsuitable
  7. app()                             — hand off to the Typer CLI

Logging is intentionally NOT fully configured here.  Full logging (log file,
log level, JSON formatter) is set up in the Typer app callback in cli.py, once
the user's --log / --verbose flags are known.  The pre-init fallback installed
here only ensures that any crash *during* startup (steps 1-6) is visible.

Long-running core components that need to honour an external stop signal should
import and check `_shutdown_event`:

    from scaldys.__main__ import _shutdown_event
    while not _shutdown_event.is_set():
        ...
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import platform
import signal
import sys
import threading
import types

from scaldys.__about__ import APP_NAME, PACKAGE_NAME, VERSION
from scaldys.cli.cli import app

__all__: list[str] = []

# ---------------------------------------------------------------------------
# Shared shutdown signal
# ---------------------------------------------------------------------------
# Set by the signal handler when SIGINT or SIGTERM is received.
# Core modules that run long loops should check this periodically to allow
# graceful shutdown without a hard kill.
_shutdown_event = threading.Event()

# ---------------------------------------------------------------------------
# Module-level logger (used by crash hook; relies on pre-init fallback until
# cli.py callback calls setup_logging)
# ---------------------------------------------------------------------------
logger = logging.getLogger(PACKAGE_NAME)


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------


def _pre_init_logging() -> None:
    """
    Install a minimal CRITICAL-only logging fallback on stderr.

    This ensures that any exception raised during startup (before the Typer
    app callback calls setup_logging()) is visible to the user rather than
    silently swallowed.  The full logging configuration (file handler, JSON
    formatter, log level) is applied later in cli.py once CLI flags are parsed.
    """
    # Use basicConfig only if no handlers are attached to the root logger yet.
    # This avoids interfering if setup_logging() was somehow already called.
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.CRITICAL,
            format="%(levelname)s: %(message)s",
            stream=sys.stderr,
        )


def _setup_crash_hook() -> None:
    """
    Replace the default sys.excepthook with one that logs unhandled exceptions.

    Without this, an unhandled exception prints a raw traceback to stderr and
    exits.  With this hook:
      - The exception is logged at CRITICAL level (captured in the log file once
        setup_logging has run, or printed to stderr via the pre-init fallback).
      - The process exits with code 1 instead of the default non-zero exit from
        the interpreter.

    In a larger project you would also send the crash report to a telemetry
    service (e.g. Sentry) from this hook before exiting.
    """

    def _excepthook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            # Let KeyboardInterrupt propagate normally so the signal handler
            # (below) controls the exit, rather than printing a traceback.
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical(
            "Unhandled exception — application will exit",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        sys.exit(1)

    sys.excepthook = _excepthook


def _setup_signal_handlers() -> None:
    """
    Install SIGINT and SIGTERM handlers for graceful shutdown.

    Both signals set the module-level _shutdown_event so that cooperative
    long-running loops can detect the stop request and finish cleanly before
    the process exits.  After setting the event the handler re-raises
    KeyboardInterrupt, which Typer/Click catches and turns into a clean exit.

    Note: signal handlers can only be installed from the main thread.  This
    function is therefore called at the very top of main() before any threads
    are started.

    On Windows, SIGTERM is not raised by the OS on Ctrl+C — only SIGINT is —
    but installing a SIGTERM handler is harmless and useful when the process is
    managed by a service manager (e.g. NSSM, systemd via WSL).
    """

    def _handler(signum: int, frame: types.FrameType | None) -> None:
        _shutdown_event.set()
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _handler)
    # SIGTERM is not available on Windows in all contexts; guard defensively.
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handler)


def _setup_asyncio_policy() -> None:
    """
    Set the appropriate asyncio event loop policy for the current platform.

    On Windows, the default event loop changed from SelectorEventLoop to
    ProactorEventLoop in Python 3.8.  ProactorEventLoop is required for:
      - subprocess support (asyncio.create_subprocess_exec / shell)
      - named pipes
      - some SSL operations

    If your application uses asyncio and needs any of these features on Windows,
    this call must happen before the first event loop is created.

    On macOS / Linux the default policy is already correct; this function is a
    no-op there.
    """
    import asyncio

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # type: ignore[attr-defined]


def _validate_environment() -> None:
    """
    Perform fast-fail environment checks before the CLI starts.

    Add project-specific checks here — for example:
      - Minimum Python version (guards against accidental use of a system Python)
      - Required environment variables (API keys, connection strings)
      - Write access to the data / log directories
      - Availability of optional native libraries

    Raise RuntimeError with a human-readable message for any failed check.
    A large project might also check network reachability, database ping, or
    the presence of a valid licence file here.
    """
    # --- Python version gate ---
    required = (3, 13)
    if sys.version_info < required:
        raise RuntimeError(
            f"{APP_NAME} requires Python {required[0]}.{required[1]} or newer; "
            f"running {sys.version}."
        )

    # --- Example: required environment variable (uncomment and adapt) ---
    # api_key = os.environ.get("MY_API_KEY")
    # if not api_key:
    #     raise RuntimeError(
    #         "Environment variable MY_API_KEY is not set. "
    #         "See the documentation for setup instructions."
    #     )

    # --- Example: writable data directory ---
    # from scaldys.common.app_location import AppLocation
    # data_dir = AppLocation.get_directory(AppLocation.AppDataDir)
    # if data_dir.exists() and not os.access(data_dir, os.W_OK):
    #     raise RuntimeError(f"Data directory is not writable: {data_dir}")

    logger.debug(
        "Environment validation passed",
        extra={
            "python_version": sys.version,
            "app_version": VERSION,
            "platform": platform.platform(),
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """
    Application entry point — runs lifecycle setup then hands off to the CLI.

    Execution order matters:
      1. freeze_support must be the very first call (multiprocessing + PyInstaller).
      2. Pre-init logging before anything that might raise an exception.
      3. Crash hook before any user code runs.
      4. Signal handlers before threads or subprocesses are spawned.
      5. Asyncio policy before any event loop is created.
      6. Environment validation before the CLI parses arguments.
      7. app() — the Typer CLI takes over from here.
    """
    multiprocessing.freeze_support()  # (1) must be first for frozen multiprocessing
    _pre_init_logging()  # (2) CRITICAL-only fallback
    _setup_crash_hook()  # (3) clean exit on unhandled exceptions
    _setup_signal_handlers()  # (4) graceful shutdown on SIGINT/SIGTERM
    _setup_asyncio_policy()  # (5) correct event loop for Windows async I/O
    _validate_environment()  # (6) fail fast on bad environment
    app()  # (7) Typer CLI — calls setup_logging via app callback


if __name__ == "__main__":
    main()
