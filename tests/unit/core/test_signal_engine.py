"""Unit tests for the signal engine (generate, FFT, metrics)."""

from typing import Any

import numpy as np
import pytest

from scaldys_template.core.signal_engine import (
    compute_fft,
    compute_metrics,
    generate_signal,
)
from scaldys_template.core.signal_model import NoiseType, SignalParameters, SignalType


def _params(**kwargs: Any) -> SignalParameters:
    """Helper: create parameters with sane defaults overridden by *kwargs*."""
    defaults: dict[str, Any] = dict(
        frequency=100.0,
        sampling_rate=8000.0,
        duration=0.1,
        fft_size=512,
    )
    defaults.update(kwargs)
    return SignalParameters(**defaults)


@pytest.mark.unit
class TestGenerateSignal:
    def test_output_shapes_match_expected_sample_count(self):
        params = _params(duration=0.1, sampling_rate=8000.0)
        sd = generate_signal(params)
        n = int(0.1 * 8000.0)
        assert len(sd.time) == n
        assert len(sd.signal) == n
        assert len(sd.noise) == n
        assert len(sd.composite) == n

    def test_time_axis_starts_at_zero(self):
        sd = generate_signal(_params())
        assert sd.time[0] == pytest.approx(0.0)

    def test_time_axis_ends_before_duration(self):
        params = _params(duration=0.1)
        sd = generate_signal(params)
        assert sd.time[-1] < params.duration

    def test_sine_amplitude_matches(self):
        params = _params(amplitude=2.0, signal_type=SignalType.SINE)
        sd = generate_signal(params)
        # Peak should be close to amplitude (within 1 sample rounding)
        assert np.max(np.abs(sd.signal)) == pytest.approx(2.0, abs=0.01)

    def test_no_noise_by_default(self):
        sd = generate_signal(_params())
        assert np.all(sd.noise == 0.0)

    def test_composite_equals_signal_plus_noise_plus_dc(self):
        params = _params(dc_offset=0.5, noise_type=NoiseType.GAUSSIAN, snr_db=20.0)
        sd = generate_signal(params)
        expected = sd.signal + sd.noise + params.dc_offset
        np.testing.assert_allclose(sd.composite, expected)

    def test_gaussian_noise_has_correct_snr(self):
        params = _params(noise_type=NoiseType.GAUSSIAN, snr_db=20.0, amplitude=1.0)
        sd = generate_signal(params)
        signal_power = np.mean(sd.signal**2)
        noise_power = np.mean(sd.noise**2)
        measured_snr = 10.0 * np.log10(signal_power / noise_power)
        # Allow ±3 dB tolerance (stochastic)
        assert abs(measured_snr - 20.0) < 3.0

    def test_all_signal_types_produce_output(self):
        for st in SignalType:
            params = _params(signal_type=st)
            sd = generate_signal(params)
            assert len(sd.composite) > 0

    def test_dc_offset_shifts_mean(self):
        params = _params(dc_offset=5.0, signal_type=SignalType.SINE)
        sd = generate_signal(params)
        assert np.mean(sd.composite) == pytest.approx(5.0, abs=0.01)


@pytest.mark.unit
class TestComputeFFT:
    def test_frequency_bins_length(self):
        params = _params(fft_size=512)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        # rfft gives fft_size // 2 + 1 bins
        assert len(fft.frequencies) == 512 // 2 + 1
        assert len(fft.magnitude_db) == len(fft.frequencies)
        assert len(fft.phase_deg) == len(fft.frequencies)

    def test_dc_offset_appears_at_bin_zero(self):
        params = _params(dc_offset=1.0, signal_type=SignalType.SINE, fft_size=512)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        # Bin 0 (DC) should not be -inf
        assert np.isfinite(fft.magnitude_db[0])

    def test_sine_peak_near_correct_frequency(self):
        freq = 1000.0
        params = _params(frequency=freq, sampling_rate=16000.0, fft_size=1024, duration=0.1)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        peak_idx = int(np.argmax(fft.magnitude_db))
        peak_freq = fft.frequencies[peak_idx]
        # Peak bin should be within one bin width of true frequency
        bin_width = sd.sample_rate / params.fft_size
        assert abs(peak_freq - freq) <= bin_width

    def test_magnitude_is_finite(self):
        sd = generate_signal(_params())
        fft = compute_fft(sd, _params())
        assert np.all(np.isfinite(fft.magnitude_db))

    def test_phase_in_expected_range(self):
        sd = generate_signal(_params())
        fft = compute_fft(sd, _params())
        assert np.all(fft.phase_deg >= -180.0)
        assert np.all(fft.phase_deg <= 180.0)


@pytest.mark.unit
class TestComputeMetrics:
    def test_rms_sine_is_amplitude_over_sqrt2(self):
        amplitude = 2.0
        params = _params(amplitude=amplitude, signal_type=SignalType.SINE)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        metrics = compute_metrics(sd, fft)
        expected_rms = amplitude / (2.0**0.5)
        assert metrics.rms == pytest.approx(expected_rms, rel=0.01)

    def test_peak_equals_amplitude_for_clean_sine(self):
        amplitude = 3.0
        params = _params(amplitude=amplitude, signal_type=SignalType.SINE)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        metrics = compute_metrics(sd, fft)
        assert metrics.peak == pytest.approx(amplitude, abs=0.01)

    def test_crest_factor_sine_is_sqrt2(self):
        params = _params(signal_type=SignalType.SINE)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        metrics = compute_metrics(sd, fft)
        assert metrics.crest_factor == pytest.approx(2.0**0.5, rel=0.02)

    def test_snr_is_none_without_noise(self):
        params = _params(noise_type=NoiseType.NONE)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        metrics = compute_metrics(sd, fft)
        assert metrics.snr_db is None

    def test_snr_is_float_with_noise(self):
        params = _params(noise_type=NoiseType.GAUSSIAN, snr_db=30.0)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        metrics = compute_metrics(sd, fft)
        assert metrics.snr_db is not None
        assert isinstance(metrics.snr_db, float)

    def test_peak_freq_near_fundamental(self):
        freq = 500.0
        params = _params(frequency=freq, sampling_rate=8000.0, fft_size=512, duration=0.1)
        sd = generate_signal(params)
        fft = compute_fft(sd, params)
        metrics = compute_metrics(sd, fft)
        bin_width = params.sampling_rate / params.fft_size
        assert abs(metrics.peak_freq - freq) <= bin_width
