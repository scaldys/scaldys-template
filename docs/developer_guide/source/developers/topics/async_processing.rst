.. _async_processing_guide:

***********************
Async Processing Pipeline
***********************

``core/async_processor.py`` is a fully documented reference implementation
showing how to run concurrent async work from a synchronous Typer command.
This page explains each design decision in detail.

.. contents:: On this page
   :local:
   :depth: 2


Public interface
================

The only symbol callers should import is ``process_items``:

.. code-block:: python

    from scaldys_template.core.async_processor import process_items, ProcessingResult

    results: list[ProcessingResult] = process_items(
        item_ids=[1, 2, 3, 4, 5],
        on_progress=lambda r: print(r.item_id, r.success),
        timeout_per_item=5.0,
    )

Everything else (``_run_pipeline``, ``_process_item``, ``_BATCH_SIZE``) is
internal.  Commands stay fully synchronous and never touch an event loop.


``ProcessingResult`` dataclass
===============================

Every item — whether it succeeded, failed, or timed out — produces a
``ProcessingResult``:

.. code-block:: python

    @dataclass
    class ProcessingResult:
        item_id: int
        value: float | None    # None on failure
        elapsed_ms: float
        error: str | None      # None on success

        @property
        def success(self) -> bool:
            return self.error is None

Using a typed dataclass rather than a dict or tuple makes error handling
explicit: callers check ``result.success`` rather than testing for ``None``
or catching exceptions.


Batching and cooperative shutdown
===================================

Items are processed in batches of ``_BATCH_SIZE`` (default 20).  Between
batches, the pipeline checks ``_shutdown_event``:

.. code-block:: python

    for batch_start in range(0, len(item_ids), _BATCH_SIZE):
        if _shutdown_event.is_set():
            logger.info("Shutdown event detected — stopping pipeline early")
            break
        batch = item_ids[batch_start : batch_start + _BATCH_SIZE]
        ...

**Why batches instead of checking per-item?**

If ``_shutdown_event`` were checked after every single item, the loop overhead
would be significant for large inputs.  The batch granularity gives a
reasonable bound on shutdown latency (at most one full batch duration) while
keeping the inner loop tight.

**Why not asyncio cancellation?**

``asyncio.CancelledError`` propagates into coroutines at the next ``await``
point, which can leave data in an inconsistent state if the coroutine has
partially committed a write.  Checking a flag at the batch boundary means
every batch either completes fully or is never started — there is no
half-processed batch.


``return_exceptions=True``
===========================

.. code-block:: python

    raw_results = await asyncio.gather(*wrapped, return_exceptions=True)

With ``return_exceptions=True``, a coroutine that raises an exception returns
the exception *object* as its result instead of cancelling all sibling
coroutines.  This means:

* One slow or broken item does not affect the others.
* All items get a ``ProcessingResult``, even failures.
* The caller sees the full picture, not just the first error.

The result-normalisation loop after ``gather`` handles three outcome types:
``ProcessingResult`` (success), ``asyncio.TimeoutError`` (per-item timeout),
and any other ``BaseException`` (unexpected error).


Per-item timeout
================

.. code-block:: python

    wrapped = [
        asyncio.wait_for(_process_item(item_id, timeout_per_item), timeout=timeout_per_item)
        for item_id in batch
    ]

``asyncio.wait_for`` cancels the coroutine if it does not complete within
``timeout_per_item`` seconds and raises ``asyncio.TimeoutError``.  The
``return_exceptions=True`` gather catches this as a result value, and the
normalisation loop converts it to a ``ProcessingResult`` with
``error="Timed out after X.Xs"``


Sync wrapper boundary
=====================

.. code-block:: python

    def process_items(...) -> list[ProcessingResult]:
        try:
            results = asyncio.run(_run_pipeline(...))
        except KeyboardInterrupt:
            logger.warning("Processing interrupted by user")
            results = []
        ...
        return results

``asyncio.run()`` creates a new event loop, runs the coroutine to completion,
and tears the loop down.  The calling command function is entirely synchronous;
it does not need to know that async code runs inside.

The ``KeyboardInterrupt`` catch at this boundary prevents
"Task was destroyed but it is pending!" warnings that would otherwise appear
when the user presses Ctrl+C while items are in flight.  ``asyncio.run()``
cancels the main task on ``KeyboardInterrupt``, but pending tasks in sub-gather
calls may still emit warnings; the try/except suppresses those from reaching
the user.


Progress callback
=================

The ``on_progress`` parameter is a plain ``Callable[[ProcessingResult], None]``
— not a Rich progress bar, not a queue, not a specific UI class.  This
decouples the pipeline from the presentation layer:

.. code-block:: python

    # In cmd_process.py:
    with Progress(...) as progress:
        task = progress.add_task("Processing…", total=num_tasks)
        def update(result: ProcessingResult) -> None:
            progress.advance(task)
        results = process_items(ids, on_progress=update)

The callback is invoked synchronously from inside the async event loop (via
``asyncio.run``), so it must not block or call ``asyncio.run()`` recursively.
Calling ``progress.advance()`` is safe — Rich's ``Progress`` is thread-safe.


Replacing the stub
==================

``_process_item`` is a stub that simulates I/O latency with ``asyncio.sleep``
and returns a trivial result.  Replace it with your real async operation:

.. code-block:: python

    async def _process_item(item_id: int, timeout_per_item: float) -> ProcessingResult:
        import time
        start = time.monotonic()

        # Real async I/O — e.g.:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.example.com/items/{item_id}") as resp:
                data = await resp.json()

        elapsed_ms = (time.monotonic() - start) * 1000.0
        return ProcessingResult(item_id=item_id, value=data["score"], elapsed_ms=elapsed_ms)

Keep the function signature (``item_id: int, timeout_per_item: float``) and
return type (``ProcessingResult``) unchanged.  The wrapper
(``asyncio.wait_for``) and the result normalisation loop require them.
