"""Unit tests for parameter_store save/load round-trip."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from scaldys_template.core.parameter_store import load_parameters, save_parameters
from scaldys_template.core.signal_model import NoiseType, SignalParameters, SignalType


@pytest.mark.unit
class TestSaveLoad:
    def test_round_trip_defaults(self, tmp_path: Path):
        original = SignalParameters()
        path = tmp_path / "params.json"
        save_parameters(original, path)
        restored = load_parameters(path)
        assert restored == original

    def test_round_trip_custom_values(self, tmp_path: Path):
        original = SignalParameters(
            signal_type=SignalType.SAWTOOTH,
            frequency=440.0,
            amplitude=0.5,
            duration=1.0,
            sampling_rate=44100.0,
            noise_type=NoiseType.UNIFORM,
            snr_db=15.0,
            fft_size=2048,
        )
        path = tmp_path / "params.json"
        save_parameters(original, path)
        restored = load_parameters(path)
        assert restored == original

    def test_save_creates_parent_directories(self, tmp_path: Path):
        path = tmp_path / "sub" / "dir" / "params.json"
        save_parameters(SignalParameters(), path)
        assert path.exists()

    def test_load_invalid_json_raises_os_or_validation_error(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json at all", encoding="utf-8")
        with pytest.raises(Exception):
            load_parameters(bad_file)

    def test_load_invalid_params_raises_validation_error(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        # Valid JSON but invalid parameters (frequency out of range)
        bad_file.write_text('{"frequency": -999}', encoding="utf-8")
        with pytest.raises(ValidationError):
            load_parameters(bad_file)

    def test_load_nonexistent_file_raises_os_error(self, tmp_path: Path):
        with pytest.raises(OSError):
            load_parameters(tmp_path / "nonexistent.json")

    def test_saved_file_is_readable_json(self, tmp_path: Path):
        import json

        path = tmp_path / "params.json"
        save_parameters(SignalParameters(), path)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "frequency" in data
        assert "signal_type" in data
