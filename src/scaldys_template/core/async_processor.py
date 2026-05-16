# -*- coding: utf-8 -*-
# cython: language_level=3

"""
Async processing pipeline — template / reference implementation.

This module shows how to structure async work so it can be called cleanly from
a synchronous Typer CLI command.  The public surface is intentionally small:

    results = process_items(item_ids, on_progress=my_callback, timeout_per_item=5.0)

Everything inside is async; the caller never touches an event loop.

Key patterns demonstrated
--------------------------
- Dataclass as a typed result container (ProcessingResult)
- Per-item async stub that simulates I/O latency (asyncio.sleep)
- Pipeline function using asyncio.gather with return_exceptions=True so one
  failing item does not cancel the rest
- Per-item timeout via asyncio.wait_for
- Progress callback protocol (callable, not a dependency on any specific UI)
- Graceful cancellation: if the caller sets _shutdown_event the pipeline drains
  its current batch and exits early rather than being killed mid-flight
- Clean sync wrapper (process_items) using asyncio.run() — the only place the
  event loop is created; commands that call this function stay fully synchronous
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Callable

from scaldys_template.__about__ import PACKAGE_NAME

__all__ = ["ProcessingResult", "process_items"]

logger = logging.getLogger(PACKAGE_NAME)

# Batch size for cooperative shutdown checks.  The pipeline processes items in
# groups of this size; between batches it checks _shutdown_event.
_BATCH_SIZE = 20


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ProcessingResult:
    """
    Container for the outcome of processing a single item.

    Attributes
    ----------
    item_id : int
        The identifier of the processed item.
    value : float | None
        The computed result, or None if processing failed.
    elapsed_ms : float
        Wall-clock time spent processing this item, in milliseconds.
    error : str | None
        Human-readable error message if processing failed, otherwise None.
    """

    item_id: int
    value: float | None
    elapsed_ms: float
    error: str | None = field(default=None)

    @property
    def success(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# Internal async implementation
# ---------------------------------------------------------------------------


class _ItemProcessingError(Exception):
    """Raised internally when stub processing fails for an item."""


async def _process_item(item_id: int, timeout_per_item: float) -> ProcessingResult:
    """
    Stub for an async I/O-bound operation on a single item.

    In a real implementation this would be:
      - An aiohttp / httpx request to an external API
      - An async database query (e.g. asyncpg, aiosqlite)
      - Reading / writing a file with aiofiles
      - Calling an async SDK (e.g. AsyncAnthropic)

    This stub uses asyncio.sleep to simulate latency and randomly raises an
    error on ~15% of items so error-handling paths are exercised.
    """
    import time

    start = time.monotonic()

    # Simulate variable I/O latency: 0–(timeout_per_item * 0.8) seconds.
    simulated_delay = random.uniform(0.0, timeout_per_item * 0.8)
    await asyncio.sleep(simulated_delay)

    elapsed_ms = (time.monotonic() - start) * 1000.0

    # Simulate ~15% error rate to demonstrate error-handling paths.
    if random.random() < 0.15:
        raise _ItemProcessingError(f"Stub processing failed for item {item_id} (simulated error)")

    # Stub result: a simple function of item_id.
    value = float(item_id * 2)
    return ProcessingResult(item_id=item_id, value=value, elapsed_ms=elapsed_ms)


async def _run_pipeline(
    item_ids: list[int],
    on_progress: Callable[[ProcessingResult], None] | None,
    timeout_per_item: float,
) -> list[ProcessingResult]:
    """
    Process all items concurrently, in batches, with per-item timeouts.

    Returns a list of ProcessingResult — one per item.  Items that timed out
    or raised an exception are represented with error != None.

    Parameters
    ----------
    item_ids : list[int]
        Identifiers of the items to process.
    on_progress : callable or None
        Called after each item completes (success or failure).  Receives the
        ProcessingResult.  Use this to update a progress bar or log status.
    timeout_per_item : float
        Maximum seconds to wait for a single item before treating it as failed.
    """
    # Import here to avoid a circular import if __main__ is not yet loaded
    # (e.g. during unit tests that import this module directly).
    try:
        from scaldys_template.__main__ import _shutdown_event
    except ImportError:
        import threading

        _shutdown_event = threading.Event()  # fallback: never set

    all_results: list[ProcessingResult] = []

    # Process in batches so we can check the shutdown event between batches
    # without leaving a large number of tasks in flight.
    for batch_start in range(0, len(item_ids), _BATCH_SIZE):
        if _shutdown_event.is_set():
            logger.info("Shutdown event detected — stopping pipeline early")
            break

        batch = item_ids[batch_start : batch_start + _BATCH_SIZE]

        # Wrap each item coroutine with a per-item timeout.
        wrapped = [
            asyncio.wait_for(_process_item(item_id, timeout_per_item), timeout=timeout_per_item)
            for item_id in batch
        ]

        # return_exceptions=True: a failed item returns the exception as its
        # result instead of cancelling all sibling tasks.
        raw_results = await asyncio.gather(*wrapped, return_exceptions=True)

        for item_id, outcome in zip(batch, raw_results):
            if isinstance(outcome, ProcessingResult):
                result = outcome
            elif isinstance(outcome, asyncio.TimeoutError):
                result = ProcessingResult(
                    item_id=item_id,
                    value=None,
                    elapsed_ms=timeout_per_item * 1000.0,
                    error=f"Timed out after {timeout_per_item:.1f}s",
                )
            elif isinstance(outcome, BaseException):
                result = ProcessingResult(
                    item_id=item_id,
                    value=None,
                    elapsed_ms=0.0,
                    error=str(outcome),
                )
            else:
                # Should never happen — asyncio.gather returns either a result
                # or an exception when return_exceptions=True.
                result = ProcessingResult(
                    item_id=item_id,
                    value=None,
                    elapsed_ms=0.0,
                    error="Unknown outcome from asyncio.gather",
                )

            logger.debug(
                "Item processed",
                extra={
                    "item_id": item_id,
                    "success": result.success,
                    "elapsed_ms": result.elapsed_ms,
                },
            )
            if on_progress is not None:
                on_progress(result)

            all_results.append(result)

    return all_results


# ---------------------------------------------------------------------------
# Public sync wrapper
# ---------------------------------------------------------------------------


def process_items(
    item_ids: list[int],
    on_progress: Callable[[ProcessingResult], None] | None = None,
    timeout_per_item: float = 10.0,
) -> list[ProcessingResult]:
    """
    Process a list of items concurrently and return the results.

    This is the public, synchronous entry point.  It creates and tears down an
    asyncio event loop internally; callers remain fully synchronous and do not
    need to manage event loops.

    Parameters
    ----------
    item_ids : list[int]
        Identifiers of items to process.
    on_progress : callable or None
        Optional callback invoked after each item completes.  Receives a
        ProcessingResult.  Useful for updating a progress bar or printing
        per-item status.
    timeout_per_item : float
        Maximum seconds to wait for a single item.  Defaults to 10.0.

    Returns
    -------
    list[ProcessingResult]
        One result per item, in the same order as item_ids.  Check
        result.success / result.error to distinguish successes from failures.

    Notes
    -----
    KeyboardInterrupt is caught here to ensure pending async tasks are
    cancelled cleanly before propagating the interrupt upward.  Without this,
    Python may print "Task was destroyed but it is pending!" warnings.
    """
    logger.info(
        "Starting async processing pipeline",
        extra={"num_items": len(item_ids), "timeout_per_item": timeout_per_item},
    )

    try:
        results = asyncio.run(_run_pipeline(item_ids, on_progress, timeout_per_item))
    except KeyboardInterrupt:
        # asyncio.run() cancels the main task on KeyboardInterrupt, but we
        # want to return whatever was completed rather than raising to the CLI.
        logger.warning("Processing interrupted by user")
        results = []

    successes = sum(1 for r in results if r.success)
    failures = len(results) - successes
    logger.info(
        "Async processing pipeline finished",
        extra={"total": len(results), "successes": successes, "failures": failures},
    )
    return results
