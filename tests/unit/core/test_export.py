# -*- coding: utf-8 -*-

"""
Unit tests for scaldys.core.export (export_data).

Patterns demonstrated
----------------------
- tmp_path for isolated filesystem tests (no isolated_app_location needed here
  because export_data receives its paths as arguments, not from AppLocation).
- Asserting exact JSON file content.
- monkeypatch to simulate an OSError from builtins.open.
- caplog to assert that errors are logged before re-raising.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from scaldys_template.core.export import export_data


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """A minimal stub config file."""
    p = tmp_path / "config.yml"
    p.write_text("version: 1\n", encoding="utf-8")
    return p


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """A non-existing output directory inside tmp_path."""
    return tmp_path / "output"


# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportData:
    def test_creates_output_directory(self, config_file: Path, output_dir: Path):
        assert not output_dir.exists()
        export_data(config_file, output_dir, num_values=0)
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_creates_data_json_file(self, config_file: Path, output_dir: Path):
        export_data(config_file, output_dir, num_values=3)
        assert (output_dir / "data.json").exists()

    def test_zero_values_produces_empty_dict(self, config_file: Path, output_dir: Path):
        export_data(config_file, output_dir, num_values=0)
        content = json.loads((output_dir / "data.json").read_text())
        assert content == {}

    @pytest.mark.parametrize("n", [1, 5, 10])
    def test_correct_number_of_keys(self, config_file: Path, output_dir: Path, n: int):
        export_data(config_file, output_dir, num_values=n)
        content = json.loads((output_dir / "data.json").read_text())
        assert len(content) == n

    def test_key_value_pairs_are_correct(self, config_file: Path, output_dir: Path):
        export_data(config_file, output_dir, num_values=4)
        content = json.loads((output_dir / "data.json").read_text())
        # Formula: key_N → N * 2
        assert content == {"key_0": 0, "key_1": 2, "key_2": 4, "key_3": 6}

    def test_output_dir_already_exists_is_ok(self, config_file: Path, output_dir: Path):
        """export_data uses exist_ok=True; calling it twice must not raise."""
        export_data(config_file, output_dir, num_values=1)
        export_data(config_file, output_dir, num_values=1)  # second call — no exception

    def test_os_error_is_logged_and_reraised(
        self, config_file: Path, output_dir: Path, caplog: pytest.LogCaptureFixture
    ):
        """When the file cannot be written, OSError must be logged at ERROR
        level and then re-raised so the caller knows the operation failed.

        Trigger: create a *directory* named data.json inside the output dir.
        When export_data tries to open("data.json", "w"), the OS raises
        IsADirectoryError (subclass of OSError) because a dir with that name
        already exists.  This is more reliable than patching builtins.open
        because Path.open() doesn't always go through builtins on all platforms.
        """
        import logging

        # Pre-create the output dir and a collision directory named data.json.
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "data.json").mkdir()  # dir with the same name as the output file

        with caplog.at_level(logging.ERROR, logger="scaldys_template"):
            with pytest.raises(OSError):
                export_data(config_file, output_dir, num_values=2)

        assert any("Failed to export" in r.message for r in caplog.records)
