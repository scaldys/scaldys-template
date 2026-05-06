# -*- coding: utf-8 -*-

"""
Integration tests for the `scaldys process` command.

These tests run the full CLI chain without mocking process_items.
The async processing pipeline executes for real — item delays are real
asyncio.sleep calls, and the ~15 % random failure rate means the exit
code may be 0 or 1 depending on the run.

For tests that need deterministic results (specific exit code assertions),
we either:
  a) Use --timeout 0.01 to force timeouts (all items fail → exit 1).
  b) Use --num-tasks 0 — not possible (min=1), so we rely on output shape.
  c) Or accept that the test only asserts on output structure, not exit code.

Patterns demonstrated
----------------------
- Integration tests that tolerate non-determinism by asserting on output
  *structure* (presence of expected strings) rather than exact values.
- Forcing a known failure mode (very short timeout → all timeout → exit 1).
- @pytest.mark.slow for tests that actually run the async pipeline.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from scaldys.cli.cli import app


runner = CliRunner()


# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
class TestCliProcessIntegration:
    def test_process_runs_without_crashing(self, isolated_app_location):
        """Smoke test: any exit code is acceptable as long as no exception leaks."""
        result = runner.invoke(app, ["process", "--num-tasks", "2", "--timeout", "5"])
        # Exit code 0 (all pass) or 1 (some fail) — both are valid outcomes.
        assert result.exit_code in (0, 1), result.output

    def test_output_contains_item_lines(self, isolated_app_location):
        result = runner.invoke(app, ["process", "--num-tasks", "3", "--timeout", "5"])
        # Each processed item emits a line containing "item"
        assert "item" in result.output

    def test_output_contains_summary_section(self, isolated_app_location):
        result = runner.invoke(app, ["process", "--num-tasks", "2", "--timeout", "5"])
        assert "Processed" in result.output
        assert "Succeeded" in result.output

    def test_very_short_timeout_forces_all_failures(self, isolated_app_location, mocker):
        """Force all items to fail by patching _process_item to sleep far
        beyond the timeout.  We use mocker even in integration context here
        because the 'async sleep > timeout' outcome cannot be guaranteed
        reliably on all hardware with real asyncio timers."""
        import asyncio
        import scaldys.core.async_processor as _mod

        async def _always_slow(item_id: int, timeout_per_item: float):
            await asyncio.sleep(10)  # always exceeds timeout_per_item
            return _mod.ProcessingResult(item_id=item_id, value=0.0, elapsed_ms=0.0)

        mocker.patch.object(_mod, "_process_item", side_effect=_always_slow)
        result = runner.invoke(app, ["process", "--num-tasks", "3", "--timeout", "0.05"])
        assert result.exit_code == 1

    def test_timeout_failures_appear_in_output(self, isolated_app_location, mocker):
        """When all items time out, FAIL must appear in the progress output."""
        import asyncio
        import scaldys.core.async_processor as _mod

        async def _always_slow(item_id: int, timeout_per_item: float):
            await asyncio.sleep(10)
            return _mod.ProcessingResult(item_id=item_id, value=0.0, elapsed_ms=0.0)

        mocker.patch.object(_mod, "_process_item", side_effect=_always_slow)
        result = runner.invoke(app, ["process", "--num-tasks", "2", "--timeout", "0.05"])
        assert "FAIL" in result.output

    def test_global_verbose_flag_works_with_process(self, isolated_app_location):
        """--verbose before the subcommand name must not cause an argument error."""
        result = runner.invoke(app, ["--verbose", "process", "--num-tasks", "1", "--timeout", "5"])
        assert result.exit_code in (0, 1), result.output

    def test_log_file_is_written(self, isolated_app_location):
        """The JSON log file must be created for the process command too."""
        runner.invoke(app, ["process", "--num-tasks", "1", "--timeout", "5"])
        log_dir = isolated_app_location[3]
        jsonl_files = list(log_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1
