# -*- coding: utf-8 -*-
# cython: language_level=3

"""
`process` CLI command — reference implementation.

Demonstrates how a CLI command orchestrates several advanced core patterns:

  - Calling an async processing pipeline from a synchronous Typer command
    (via core.async_processor.process_items)
  - Opening a database connection for the lifetime of the command
    (via core.database.DatabaseConnection + transaction)
  - Progress reporting via a callback (no third-party progress library needed)
  - Graceful handling of partial results on KeyboardInterrupt
  - Structured logging of per-command metrics
  - Appropriate exit code (1) when any items fail

Invocation examples
--------------------
    scaldys process                          # 10 tasks, 5.0 s timeout per task
    scaldys process --num-tasks 50           # 50 tasks
    scaldys process --num-tasks 20 --timeout 1.0   # 20 tasks, 1 s timeout
    scaldys --log debug process --num-tasks 5      # verbose logging
"""

from __future__ import annotations

import logging
from typing import Annotated

import typer

from scaldys.__about__ import APP_NAME, PACKAGE_NAME, VERSION
from scaldys.core.async_processor import ProcessingResult, process_items
from scaldys.core.database import DatabaseConfig, DatabaseConnection, transaction

__all__ = ["process"]

logger = logging.getLogger(PACKAGE_NAME)

# ---------------------------------------------------------------------------
# Command-local argument type definitions
# ---------------------------------------------------------------------------

ARG_TYPE_NUM_TASKS = Annotated[
    int,
    typer.Option(
        "--num-tasks",
        "-n",
        help="Number of items to process.",
        min=1,
        max=10_000,
    ),
]

ARG_TYPE_TIMEOUT = Annotated[
    float,
    typer.Option(
        "--timeout",
        "-t",
        help="Maximum seconds to wait for each individual item before it is marked as timed out.",
        min=0.01,
    ),
]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def process(
    ctx: typer.Context,
    num_tasks: ARG_TYPE_NUM_TASKS = 10,
    timeout: ARG_TYPE_TIMEOUT = 5.0,
) -> None:
    """
    Run the async processing pipeline against a set of stub items.

    Demonstrates:
      - Async processing called from a sync CLI command
      - Database connection / transaction lifecycle
      - Progress callback pattern
      - Graceful interrupt handling
      - Structured per-command result summary
    """
    logger.info(
        f"Starting {APP_NAME} version {VERSION} — process command",
        extra={"num_tasks": num_tasks, "timeout": timeout},
    )

    item_ids = list(range(1, num_tasks + 1))

    # ------------------------------------------------------------------
    # Progress tracking
    # ------------------------------------------------------------------
    # A simple mutable counter is enough for a callback-based progress report.
    # In a richer application you could pass a typer.progressbar context manager
    # or a rich.progress.Progress instance into the callback instead.
    completed: list[ProcessingResult] = []

    def _on_progress(result: ProcessingResult) -> None:
        completed.append(result)
        status = "OK" if result.success else f"FAIL ({result.error})"
        typer.echo(
            f"  [{len(completed):>{len(str(num_tasks))}}/{num_tasks}] "
            f"item {result.item_id:>5}  {result.elapsed_ms:6.1f} ms  {status}"
        )

    # ------------------------------------------------------------------
    # Database connection (stub)
    # ------------------------------------------------------------------
    # Opens a connection for the entire lifetime of the command and uses a
    # transaction to record the run in a stub log table.  Replace DatabaseConfig
    # with values loaded from AppSettings or environment variables.
    db_config = DatabaseConfig(host="localhost", name="appdb", user="appuser")

    typer.echo(
        f"\nConnecting to database '{db_config.name}' on {db_config.host}:{db_config.port}..."
    )
    logger.debug("Opening database connection for process command", extra={"db": db_config.name})

    # Initialize here so pyright knows these are always bound even if the `with`
    # block raises before reaching the assignments inside it.
    results: list[ProcessingResult] = []
    successes: list[ProcessingResult] = []
    failures: list[ProcessingResult] = []

    with DatabaseConnection(db_config) as conn:
        # Record the start of this run inside a transaction.
        with transaction(conn):
            conn.execute(
                "INSERT INTO run_log (command, num_tasks, status) VALUES (%s, %s, %s)",
                ("process", num_tasks, "started"),
            )

        # ------------------------------------------------------------------
        # Async processing pipeline
        # ------------------------------------------------------------------
        typer.echo(f"\nProcessing {num_tasks} item(s) with timeout={timeout}s per item...\n")

        try:
            results = process_items(
                item_ids,
                on_progress=_on_progress,
                timeout_per_item=timeout,
            )
        except KeyboardInterrupt:
            # process_items handles KeyboardInterrupt internally and returns
            # whatever completed, but in case it propagates upward we handle
            # it here too so the summary is still printed.
            typer.echo("\nInterrupted by user.")
            results = completed

        # ------------------------------------------------------------------
        # Persist results (stub)
        # ------------------------------------------------------------------
        # In a real application you would bulk-insert results into the database.
        # Shown here as a single stubbed call inside a transaction.
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        with transaction(conn):
            conn.execute(
                "UPDATE run_log SET status = %s, success_count = %s, failure_count = %s "
                "WHERE command = %s AND status = %s",
                ("finished", len(successes), len(failures), "process", "started"),
            )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    _print_summary(results, num_tasks)

    logger.info(
        "Process command finished",
        extra={"completed": len(results), "successes": len(successes), "failures": len(failures)},
    )

    if failures:
        raise typer.Exit(code=1)


def _print_summary(results: list[ProcessingResult], num_tasks: int) -> None:
    """Print a concise result summary to stdout."""
    if not results:
        typer.echo("\nNo items were processed.")
        return

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    avg_ms = sum(r.elapsed_ms for r in results) / len(results)

    typer.echo("\n" + "-" * 50)
    typer.echo(f"  Processed : {len(results)}/{num_tasks}")
    typer.echo(f"  Succeeded : {len(successes)}")
    typer.echo(f"  Failed    : {len(failures)}")
    typer.echo(f"  Avg time  : {avg_ms:.1f} ms/item")

    if failures:
        typer.echo("\n  Failed items:")
        for r in failures:
            typer.echo(f"    item {r.item_id}: {r.error}", err=True)

    typer.echo("-" * 50 + "\n")
