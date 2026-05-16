# -*- coding: utf-8 -*-

"""
Unit tests for scaldys.core.async_processor.

Patterns demonstrated
----------------------
- Monkeypatching an async function (_process_item) with a deterministic stub
  to make random-behaviour code testable.
- Testing the public sync wrapper (process_items) — callers never touch asyncio.
- Testing the internal coroutine (_run_pipeline) directly using pytest-asyncio
  (async def test_ is automatically treated as an asyncio test via asyncio_mode="auto").
- Asserting on structured result objects rather than raw output.
- Testing cancellation / timeout paths.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

import scaldys_template.core.async_processor as _mod
from scaldys_template.core.async_processor import ProcessingResult, process_items


# ---------------------------------------------------------------------------
# ProcessingResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProcessingResult:
    def test_success_when_no_error(self):
        r = ProcessingResult(item_id=1, value=2.0, elapsed_ms=10.0)
        assert r.success is True

    def test_failure_when_error_is_set(self):
        r = ProcessingResult(item_id=1, value=None, elapsed_ms=0.0, error="oops")
        assert r.success is False

    def test_error_defaults_to_none(self):
        r = ProcessingResult(item_id=5, value=10.0, elapsed_ms=5.0)
        assert r.error is None


# ---------------------------------------------------------------------------
# process_items (sync public wrapper)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProcessItems:
    """Tests for the synchronous process_items() entry point."""

    def test_empty_list_returns_empty(self):
        results = process_items([])
        assert results == []

    def test_returns_one_result_per_item(self, monkeypatch: pytest.MonkeyPatch):
        """With a deterministic stub each item must produce exactly one result."""

        async def _always_success(item_id: int, timeout_per_item: float) -> ProcessingResult:
            return ProcessingResult(item_id=item_id, value=float(item_id * 2), elapsed_ms=1.0)

        monkeypatch.setattr(_mod, "_process_item", _always_success)
        results = process_items([10, 20, 30])
        assert len(results) == 3

    def test_all_results_succeed_with_good_stub(self, monkeypatch: pytest.MonkeyPatch):
        async def _always_success(item_id: int, timeout_per_item: float) -> ProcessingResult:
            return ProcessingResult(item_id=item_id, value=float(item_id * 2), elapsed_ms=1.0)

        monkeypatch.setattr(_mod, "_process_item", _always_success)
        results = process_items([1, 2, 3])
        assert all(r.success for r in results)

    def test_result_values_match_item_ids(self, monkeypatch: pytest.MonkeyPatch):
        async def _always_success(item_id: int, timeout_per_item: float) -> ProcessingResult:
            return ProcessingResult(item_id=item_id, value=float(item_id * 2), elapsed_ms=1.0)

        monkeypatch.setattr(_mod, "_process_item", _always_success)
        results = process_items([5])
        assert results[0].item_id == 5
        assert results[0].value == 10.0

    def test_exception_in_item_produces_failure_result(self, monkeypatch: pytest.MonkeyPatch):
        """An exception raised by _process_item must become a failed result,
        not an unhandled exception from process_items()."""

        async def _always_fails(item_id: int, timeout_per_item: float) -> ProcessingResult:
            raise RuntimeError("stub error")

        monkeypatch.setattr(_mod, "_process_item", _always_fails)
        results = process_items([1, 2])
        assert all(not r.success for r in results)
        assert all("stub error" in (r.error or "") for r in results)

    def test_timeout_produces_failure_result(self, monkeypatch: pytest.MonkeyPatch):
        """Items that exceed timeout_per_item must appear as failures."""

        async def _slow(item_id: int, timeout_per_item: float) -> ProcessingResult:
            await asyncio.sleep(10)  # longer than any timeout we pass
            return ProcessingResult(item_id=item_id, value=0.0, elapsed_ms=0.0)

        monkeypatch.setattr(_mod, "_process_item", _slow)
        results = process_items([1], timeout_per_item=0.05)
        assert len(results) == 1
        assert not results[0].success
        assert "Timed out" in (results[0].error or "")

    def test_progress_callback_called_once_per_item(self, monkeypatch: pytest.MonkeyPatch):
        async def _always_success(item_id: int, timeout_per_item: float) -> ProcessingResult:
            return ProcessingResult(item_id=item_id, value=float(item_id), elapsed_ms=1.0)

        monkeypatch.setattr(_mod, "_process_item", _always_success)
        calls: list[ProcessingResult] = []
        process_items([1, 2, 3], on_progress=calls.append)
        assert len(calls) == 3


# ---------------------------------------------------------------------------
# _run_pipeline (internal async coroutine) — tested with pytest-asyncio
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunPipelineAsync:
    """Direct tests of the async pipeline coroutine using pytest-asyncio.

    asyncio_mode = "auto" in pyproject.toml means async def test_ methods
    are automatically run under asyncio — no @pytest.mark.asyncio decorator
    needed.
    """

    async def test_empty_input_returns_empty_list(self):
        from scaldys_template.core.async_processor import _run_pipeline

        results = await _run_pipeline([], on_progress=None, timeout_per_item=5.0)
        assert results == []

    async def test_single_success_item(self, monkeypatch: pytest.MonkeyPatch):
        from scaldys_template.core.async_processor import _run_pipeline

        async def _stub(item_id: int, timeout_per_item: float) -> ProcessingResult:
            return ProcessingResult(item_id=item_id, value=1.0, elapsed_ms=0.0)

        monkeypatch.setattr(_mod, "_process_item", _stub)
        results = await _run_pipeline([42], on_progress=None, timeout_per_item=5.0)
        assert len(results) == 1
        assert results[0].success
        assert results[0].item_id == 42

    async def test_progress_callback_receives_each_result(self, monkeypatch: pytest.MonkeyPatch):
        from scaldys_template.core.async_processor import _run_pipeline

        async def _stub(item_id: int, timeout_per_item: float) -> ProcessingResult:
            return ProcessingResult(item_id=item_id, value=float(item_id), elapsed_ms=0.0)

        monkeypatch.setattr(_mod, "_process_item", _stub)
        seen: list[int] = []
        await _run_pipeline(
            [1, 2, 3],
            on_progress=lambda r: seen.append(r.item_id),
            timeout_per_item=5.0,
        )
        assert sorted(seen) == [1, 2, 3]
