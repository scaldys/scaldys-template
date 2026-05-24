"""Integration tests for the ``analyze`` CLI command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaldys_template.cli.cli import app
from scaldys_template.core.signal_model import SignalParameters

runner = CliRunner()


def _write_params(path: Path, **overrides) -> None:
    """Write a valid SignalParameters JSON file to *path*."""
    params = SignalParameters(**overrides)
    path.write_text(params.model_dump_json(indent=2), encoding="utf-8")


@pytest.mark.integration
class TestAnalyzeCLI:
    def test_analyze_with_defaults_exits_zero(self, tmp_path: Path):
        out = tmp_path / "out"
        result = runner.invoke(app, ["analyze", "--output", str(out), "--no-plots"])
        assert result.exit_code == 0, result.output

    def test_analyze_creates_csv_files(self, tmp_path: Path):
        out = tmp_path / "out"
        runner.invoke(app, ["analyze", "--output", str(out), "--no-plots"])
        assert (out / "time_domain.csv").exists()
        assert (out / "frequency_domain.csv").exists()
        assert (out / "metrics.csv").exists()

    def test_analyze_from_params_file(self, tmp_path: Path):
        params_file = tmp_path / "params.json"
        _write_params(params_file, frequency=440.0, duration=0.05, fft_size=256)
        out = tmp_path / "out"
        result = runner.invoke(
            app, ["analyze", str(params_file), "--output", str(out), "--no-plots"]
        )
        assert result.exit_code == 0, result.output

    def test_analyze_fails_without_force_on_existing_output(self, tmp_path: Path):
        out = tmp_path / "out"
        out.mkdir()
        result = runner.invoke(app, ["analyze", "--output", str(out), "--no-plots"])
        assert result.exit_code != 0

    def test_analyze_force_overwrites_existing_output(self, tmp_path: Path):
        out = tmp_path / "out"
        out.mkdir()
        result = runner.invoke(app, ["analyze", "--output", str(out), "--no-plots", "--force"])
        assert result.exit_code == 0, result.output

    def test_time_domain_csv_has_expected_columns(self, tmp_path: Path):
        out = tmp_path / "out"
        runner.invoke(app, ["analyze", "--output", str(out), "--no-plots"])
        import csv

        with (out / "time_domain.csv").open(encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(row for row in reader if not row[0].startswith("#"))
        assert header == ["time_s", "signal", "noise", "composite"]

    def test_metrics_csv_contains_rms_key(self, tmp_path: Path):
        out = tmp_path / "out"
        runner.invoke(app, ["analyze", "--output", str(out), "--no-plots"])
        import csv

        keys = {}
        with (out / "metrics.csv").open(encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # header row
            for row in reader:
                if len(row) == 2:
                    keys[row[0]] = row[1]
        assert "rms" in keys
        assert float(keys["rms"]) > 0.0

    def test_analyze_invalid_params_file_exits_nonzero(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json", encoding="utf-8")
        out = tmp_path / "out"
        result = runner.invoke(app, ["analyze", str(bad_file), "--output", str(out), "--no-plots"])
        assert result.exit_code != 0
