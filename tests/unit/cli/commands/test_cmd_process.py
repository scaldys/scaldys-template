# -*- coding: utf-8 -*-

"""
Unit tests for scaldys.cli.commands.cmd_process (process command).

Patterns demonstrated
----------------------
- mocker.patch to inject deterministic results from process_items.
- Testing exit codes: 0 for all-success, 1 for any failure.
- Testing the _print_summary helper in isolation using capsys.
- Asserting stdout content with substring checks (not exact match),
  which is more resilient to minor formatting changes.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from scaldys.cli.cli import app
from scaldys.core.async_processor import ProcessingResult
from scaldys.cli.commands.cmd_process import _print_summary

runner = CliRunner()


# ---------------------------------------------------------------------------
# _print_summary (isolated unit test — no CLI overhead)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrintSummary:
    def test_empty_results_prints_message(self, capsys):
        _print_summary([], num_tasks=5)
        out, _ = capsys.readouterr()
        assert "No items" in out

    def test_shows_succeeded_and_failed_counts(self, capsys):
        results = [
            ProcessingResult(item_id=1, value=2.0, elapsed_ms=10.0),
            ProcessingResult(item_id=2, value=None, elapsed_ms=0.0, error="boom"),
        ]
        _print_summary(results, num_tasks=2)
        out, _ = capsys.readouterr()
        assert "Succeeded" in out
        assert "Failed" in out

    def test_all_success_shows_zero_failures(self, capsys):
        results = [ProcessingResult(item_id=i, value=float(i), elapsed_ms=5.0) for i in range(3)]
        _print_summary(results, num_tasks=3)
        out, _ = capsys.readouterr()
        assert "3" in out  # succeeded count


# ---------------------------------------------------------------------------
# process command via CliRunner
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProcessCommand:
    def _all_success_results(self, n: int) -> list[ProcessingResult]:
        return [
            ProcessingResult(item_id=i, value=float(i), elapsed_ms=5.0) for i in range(1, n + 1)
        ]

    def _one_failure_results(self, n: int) -> list[ProcessingResult]:
        results = self._all_success_results(n)
        results[0] = ProcessingResult(
            item_id=results[0].item_id, value=None, elapsed_ms=0.0, error="boom"
        )
        return results

    def test_help_accessible(self, isolated_app_location):
        result = runner.invoke(app, ["process", "--help"])
        assert result.exit_code == 0

    def test_exit_code_0_when_all_succeed(self, isolated_app_location, mocker):
        mocker.patch(
            "scaldys.cli.commands.cmd_process.process_items",
            return_value=self._all_success_results(3),
        )
        result = runner.invoke(app, ["process", "--num-tasks", "3"])
        assert result.exit_code == 0

    def test_exit_code_1_when_any_fail(self, isolated_app_location, mocker):
        mocker.patch(
            "scaldys.cli.commands.cmd_process.process_items",
            return_value=self._one_failure_results(3),
        )
        result = runner.invoke(app, ["process", "--num-tasks", "3"])
        assert result.exit_code == 1

    def test_output_contains_per_item_lines(self, isolated_app_location, mocker):
        mocker.patch(
            "scaldys.cli.commands.cmd_process.process_items",
            return_value=self._all_success_results(2),
        )
        result = runner.invoke(app, ["process", "--num-tasks", "2"])
        # Each item line contains the item id
        assert "item" in result.output

    def test_output_contains_summary(self, isolated_app_location, mocker):
        mocker.patch(
            "scaldys.cli.commands.cmd_process.process_items",
            return_value=self._all_success_results(2),
        )
        result = runner.invoke(app, ["process", "--num-tasks", "2"])
        assert "Succeeded" in result.output

    def test_num_tasks_is_forwarded_to_process_items(self, isolated_app_location, mocker):
        mock_pi = mocker.patch(
            "scaldys.cli.commands.cmd_process.process_items",
            return_value=[],
        )
        runner.invoke(app, ["process", "--num-tasks", "42"])
        call_args = mock_pi.call_args
        item_ids = call_args.args[0]
        assert len(item_ids) == 42

    def test_timeout_is_forwarded_to_process_items(self, isolated_app_location, mocker):
        mock_pi = mocker.patch(
            "scaldys.cli.commands.cmd_process.process_items",
            return_value=[],
        )
        runner.invoke(app, ["process", "--num-tasks", "3", "--timeout", "2.5"])
        call_kwargs = mock_pi.call_args.kwargs
        assert call_kwargs.get("timeout_per_item") == pytest.approx(2.5)
