# cython: language_level=3

"""
`process` CLI command — reference implementation.

Demonstrates how a CLI command orchestrates several advanced core patterns:

  - Calling an async processing pipeline from a synchronous Typer command
    (via core.async_processor.process_items)
  - Opening a database connection for the lifetime of the command
    (via core.database.DatabaseConnection + transaction)
  - Progress reporting via a callback with Rich progress bar
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
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from scaldys_template.__about__ import APP_NAME, PACKAGE_NAME, VERSION
from scaldys_template.core.async_processor import ProcessingResult, process_items
from scaldys_template.core.database import DatabaseConfig, DatabaseConnection, transaction

__all__ = ["process"]

logger = logging.getLogger(PACKAGE_NAME)
console = Console()
err_console = Console(stderr=True)

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
    # Database connection (stub)
    # ------------------------------------------------------------------
    db_config = DatabaseConfig(host="localhost", name="appdb", user="appuser")

    console.print(
        f"\nConnecting to database [bold cyan]{db_config.name}[/bold cyan]"
        f" on [cyan]{db_config.host}:{db_config.port}[/cyan]..."
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
        # Async processing pipeline with Rich progress bar
        # ------------------------------------------------------------------
        console.print(
            f"\nProcessing [bold]{num_tasks}[/bold] item(s)"
            f" with timeout=[cyan]{timeout}[/cyan]s per item...\n"
        )

        completed: list[ProcessingResult] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Processing items...", total=num_tasks)

            def _on_progress(result: ProcessingResult) -> None:
                completed.append(result)
                if result.success:
                    status = "[green]OK[/green]"
                else:
                    status = f"[red]FAIL ({result.error})[/red]"
                progress.console.print(
                    f"  [{len(completed):>{len(str(num_tasks))}}/{num_tasks}]"
                    f"  item {result.item_id:>5}  {result.elapsed_ms:6.1f} ms  {status}"
                )
                progress.advance(task_id)

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
                console.print("\n[yellow]Interrupted by user.[/yellow]")
                results = completed

        # ------------------------------------------------------------------
        # Persist results (stub)
        # ------------------------------------------------------------------
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
    """Print a concise result summary using a Rich panel and table."""
    if not results:
        console.print("\n[yellow]No items were processed.[/yellow]")
        return

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]
    avg_ms = sum(r.elapsed_ms for r in results) / len(results)

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Label", style="bold")
    table.add_column("Value")

    table.add_row("Processed", f"{len(results)}/{num_tasks}")
    table.add_row("Succeeded", f"[green]{len(successes)}[/green]")
    table.add_row(
        "Failed",
        f"[red]{len(failures)}[/red]" if failures else f"[green]{len(failures)}[/green]",
    )
    table.add_row("Avg time", f"{avg_ms:.1f} ms/item")

    border_style = "red" if failures else "green"
    console.print(Panel(table, title="[bold]Summary[/bold]", border_style=border_style))

    if failures:
        err_console.print("\n[bold red]Failed items:[/bold red]")
        for r in failures:
            err_console.print(f"  item {r.item_id}: [red]{r.error}[/red]")
