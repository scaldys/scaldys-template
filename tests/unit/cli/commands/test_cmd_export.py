# -*- coding: utf-8 -*-

"""
Unit tests for scaldys.cli.commands.cmd_export (export command).

Patterns demonstrated
----------------------
- typer.testing.CliRunner for invoking the CLI app in-process.
- pytest-mock's `mocker.patch` to replace core functions (export_data) so
  the unit tests do not touch the real filesystem.
- isolated_app_location to prevent logging setup from writing real log files.
- Asserting on exit code, stdout content, and mock call count.

Important: these tests invoke the Typer `app` object directly, not
`__main__.main()`.  This skips the lifecycle setup (__main__.py) and tests the
command routing + argument handling in isolation.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from scaldys_template.cli.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def invoke(*args: str, isolated=True, isolated_app_location=None) -> object:
    """Helper: invoke the CLI with the given args."""
    return runner.invoke(app, list(args))


# ---------------------------------------------------------------------------
# Basic invocation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportCommand:
    def test_help_text_accessible(self, isolated_app_location):
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
        assert "export" in result.output.lower()

    def test_export_calls_export_data(self, isolated_app_location, mocker, tmp_path):
        """export_data should be called exactly once when all args are valid."""
        mock_export = mocker.patch("scaldys_template.cli.commands.cmd_export.export_data")
        config = tmp_path / "config.yml"
        config.write_text("v: 1\n", encoding="utf-8")

        result = runner.invoke(app, ["export", str(config)])
        assert result.exit_code == 0
        mock_export.assert_called_once()

    def test_export_does_not_overwrite_existing_output_by_default(
        self, isolated_app_location, mocker, tmp_path
    ):
        """Without --force, export should log an error and NOT call export_data
        when the output directory already exists."""
        mock_export = mocker.patch("scaldys_template.cli.commands.cmd_export.export_data")
        config = tmp_path / "config.yml"
        config.write_text("v: 1\n", encoding="utf-8")
        existing_output = tmp_path / "existing_output"
        existing_output.mkdir()

        result = runner.invoke(app, ["export", str(config), str(existing_output)])
        assert result.exit_code == 0  # exits cleanly (logged error, not exception)
        mock_export.assert_not_called()

    def test_export_overwrites_with_force_flag(self, isolated_app_location, mocker, tmp_path):
        """With --force, export_data MUST be called even if output dir exists."""
        mock_export = mocker.patch("scaldys_template.cli.commands.cmd_export.export_data")
        config = tmp_path / "config.yml"
        config.write_text("v: 1\n", encoding="utf-8")
        existing_output = tmp_path / "existing_output"
        existing_output.mkdir()

        result = runner.invoke(app, ["export", str(config), str(existing_output), "--force"])
        assert result.exit_code == 0
        mock_export.assert_called_once()

    def test_num_values_is_passed_to_export_data(self, isolated_app_location, mocker, tmp_path):
        """--num_values N must be forwarded to export_data as num_values=N."""
        mock_export = mocker.patch("scaldys_template.cli.commands.cmd_export.export_data")
        config = tmp_path / "config.yml"
        config.write_text("v: 1\n", encoding="utf-8")

        runner.invoke(app, ["export", str(config), "--num_values", "7"])
        _, kwargs = mock_export.call_args
        # export_data is called positionally; check 3rd positional arg
        args = mock_export.call_args.args
        assert args[2] == 7
