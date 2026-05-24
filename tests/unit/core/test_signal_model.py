"""Unit tests for SignalParameters validation rules."""

import pytest
from pydantic import ValidationError

from scaldys_template.core.signal_model import (
    NoiseType,
    SignalParameters,
    SignalType,
    WindowType,
)


@pytest.mark.unit
class TestFieldValidators:
    def test_defaults_are_valid(self):
        p = SignalParameters()
        assert p.signal_type == SignalType.SINE
        assert p.frequency == 440.0
        assert p.noise_type == NoiseType.NONE

    def test_frequency_below_minimum_raises(self):
        with pytest.raises(ValidationError, match="Frequency"):
            SignalParameters(frequency=0.05)

    def test_frequency_above_maximum_raises(self):
        with pytest.raises(ValidationError, match="Frequency"):
            SignalParameters(frequency=10_001.0)

    def test_amplitude_zero_raises(self):
        with pytest.raises(ValidationError, match="Amplitude"):
            SignalParameters(amplitude=0.0)

    def test_amplitude_negative_raises(self):
        with pytest.raises(ValidationError, match="Amplitude"):
            SignalParameters(amplitude=-1.0)

    def test_duration_below_minimum_raises(self):
        with pytest.raises(ValidationError, match="Duration"):
            SignalParameters(duration=0.0001)

    def test_duration_above_maximum_raises(self):
        with pytest.raises(ValidationError, match="Duration"):
            SignalParameters(duration=61.0)

    def test_fft_size_not_power_of_two_raises(self):
        with pytest.raises(ValidationError, match="power of two"):
            SignalParameters(fft_size=1000)

    def test_fft_size_one_raises(self):
        with pytest.raises(ValidationError, match="≥ 2"):
            SignalParameters(fft_size=1)

    def test_phase_out_of_range_raises(self):
        with pytest.raises(ValidationError, match="Phase"):
            SignalParameters(phase_deg=361.0)


@pytest.mark.unit
class TestCrossFieldValidators:
    def test_nyquist_violation_raises(self):
        with pytest.raises(ValidationError, match="Nyquist|sampling rate|Sampling rate"):
            # sampling_rate (100) < 2 × frequency (200)
            SignalParameters(frequency=200.0, sampling_rate=100.0, fft_size=8, duration=0.1)

    def test_nyquist_exact_boundary_is_valid(self):
        # sampling_rate == 2 × frequency is acceptable
        p = SignalParameters(frequency=100.0, sampling_rate=200.0, fft_size=16, duration=0.1)
        assert p.sampling_rate == 200.0

    def test_fft_size_exceeds_total_samples_raises(self):
        # duration=0.001 s, sampling_rate=1000 Hz → 1 sample
        # fft_size=16 > 1 sample
        with pytest.raises(ValidationError, match="FFT size"):
            SignalParameters(frequency=100.0, sampling_rate=1000.0, duration=0.001, fft_size=16)

    def test_valid_complex_parameters(self):
        p = SignalParameters(
            signal_type=SignalType.SQUARE,
            frequency=440.0,
            amplitude=2.5,
            duration=0.5,
            sampling_rate=44100.0,
            phase_deg=90.0,
            dc_offset=0.1,
            noise_type=NoiseType.GAUSSIAN,
            snr_db=30.0,
            fft_window=WindowType.BLACKMAN,
            fft_size=4096,
        )
        assert p.signal_type == SignalType.SQUARE


@pytest.mark.unit
class TestSerialization:
    def test_round_trip_json(self):
        original = SignalParameters(frequency=440.0, fft_size=2048)
        json_str = original.model_dump_json()
        restored = SignalParameters.model_validate_json(json_str)
        assert restored == original

    def test_all_signal_types_serialise(self):
        for st in SignalType:
            p = SignalParameters(signal_type=st)
            restored = SignalParameters.model_validate_json(p.model_dump_json())
            assert restored.signal_type == st
