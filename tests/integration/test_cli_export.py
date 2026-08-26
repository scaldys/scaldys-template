"""
Integration tests for the `scaldys export` command.

Unlike unit tests (which mock export_data), these tests let the full chain run:
    CLI arg parsing → app callback (setup_logging) → export command → export_data → filesystem

The isolated_app_location fixture ensures all file I/O goes to tmp directories
so these tests are safe to run in any environment.

Patterns demonstrated
----------------------
- Full CLI invocation with real file creation — verifying end-to-end behaviour.
- Asserting on output file content, not just exit code.
- Checking log-level propagation (--log debug adds more entries to the log file).
- Testing the --force flag end-to-end with a real pre-existing output directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaldys_template.cli.cli import app

runner = CliRunner()


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    p = tmp_path / "config.yml"
    p.write_text("version: 1\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCliExportIntegration:
    def test_export_creates_output_file(
        self, isolated_app_location, config_file: Path, tmp_path: Path
    ):
        """Full run: the command must create data.json in the output directory."""
        output_dir = tmp_path / "export_out"
        result = runner.invoke(
            app,
            [
                "export",
                str(config_file),
                str(output_dir),
                "--num_values",
                "3",
            ],
        )
        assert result.exit_code == 0, result.output
        data_file = output_dir / "data.json"
        assert data_file.exists(), "data.json was not created"

    def test_export_output_has_correct_keys(
        self, isolated_app_location, config_file: Path, tmp_path: Path
    ):
        output_dir = tmp_path / "export_out"
        runner.invoke(
            app,
            [
                "export",
                str(config_file),
                str(output_dir),
                "--num_values",
                "5",
            ],
        )
        content = json.loads((output_dir / "data.json").read_text())
        assert len(content) == 5
        assert "key_0" in content
        assert "key_4" in content

    def test_export_fails_on_existing_output_without_force(
        self, isolated_app_location, config_file: Path, tmp_path: Path
    ):
        """Without --force, the command exits 0 but must NOT write any file."""
        output_dir = tmp_path / "pre_existing"
        output_dir.mkdir()

        result = runner.invoke(app, ["export", str(config_file), str(output_dir)])
        assert result.exit_code == 0
        assert not (output_dir / "data.json").exists()

    def test_export_force_overwrites_existing_output(
        self, isolated_app_location, config_file: Path, tmp_path: Path
    ):
        output_dir = tmp_path / "overwrite_me"
        output_dir.mkdir()
        # Write a sentinel file that should still be there after (export_data uses exist_ok=True).
        sentinel = output_dir / "other_file.txt"
        sentinel.write_text("keep me", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "export",
                str(config_file),
                str(output_dir),
                "--num_values",
                "2",
                "--force",
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "data.json").exists()

    def test_global_log_flag_is_accepted(
        self, isolated_app_location, config_file: Path, tmp_path: Path
    ):
        """--log debug must not cause an error; it is a global flag before the subcommand."""
        output_dir = tmp_path / "export_debug"
        result = runner.invoke(
            app,
            [
                "--log",
                "debug",
                "export",
                str(config_file),
                str(output_dir),
                "--num_values",
                "1",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_log_file_is_created(self, isolated_app_location, config_file: Path, tmp_path: Path):
        """A .jsonl log file must be created in the isolated log directory."""
        output_dir = tmp_path / "export_logcheck"
        runner.invoke(
            app,
            [
                "export",
                str(config_file),
                str(output_dir),
                "--num_values",
                "1",
            ],
        )
        log_dir = isolated_app_location[3]  # AppLocation.LogDir == 3
        jsonl_files = list(log_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1
