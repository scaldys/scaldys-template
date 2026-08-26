"""Signal generation, FFT computation, and metrics.

All functions are pure (no I/O, no GUI dependency) and operate on NumPy
arrays.  The public surface is small:

    signal_data = generate_signal(params)
    fft_result  = compute_fft(signal_data, params)
    metrics     = compute_metrics(signal_data, fft_result)

``SignalData``, ``FFTResult``, and ``SignalMetrics`` are dataclasses used as
typed result containers throughout the application.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from scaldys_template.__about__ import PACKAGE_NAME
from scaldys_template.core.signal_model import (
    NoiseType,
    SignalParameters,
    SignalType,
    WindowType,
)

__all__ = [
    "FFTResult",
    "SignalData",
    "SignalMetrics",
    "compute_fft",
    "compute_metrics",
    "generate_signal",
]

logger = logging.getLogger(PACKAGE_NAME)

# Floating-point floor used before log10 to avoid -inf in magnitude array.
_LOG_FLOOR = 1e-12


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class SignalData:
    """Time-domain arrays produced by ``generate_signal``."""

    time: np.ndarray  # shape (N,)  — time axis in seconds
    signal: np.ndarray  # shape (N,)  — clean waveform (no noise, no DC)
    noise: np.ndarray  # shape (N,)  — noise component (zeros if no noise)
    composite: np.ndarray  # shape (N,)  — signal + noise + dc_offset
    sample_rate: float  # Hz


@dataclass
class FFTResult:
    """Frequency-domain arrays produced by ``compute_fft``."""

    frequencies: np.ndarray  # shape (M,)  — positive frequency bins in Hz
    magnitude_db: np.ndarray  # shape (M,)  — magnitude spectrum in dB
    phase_deg: np.ndarray  # shape (M,)  — phase spectrum in degrees


@dataclass
class SignalMetrics:
    """Scalar quality metrics produced by ``compute_metrics``."""

    rms: float
    peak: float
    crest_factor: float  # peak / RMS
    snr_db: float | None  # None when no additive noise was requested
    thd_db: float  # Total Harmonic Distortion (simplified)
    peak_freq: float  # Hz — dominant frequency bin


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_window(arr: np.ndarray, window_type: WindowType) -> np.ndarray:
    n = len(arr)
    match window_type:
        case WindowType.HANNING:
            w = np.hanning(n)
        case WindowType.HAMMING:
            w = np.hamming(n)
        case WindowType.BLACKMAN:
            w = np.blackman(n)
        case _:  # RECTANGULAR — no windowing
            w = np.ones(n)
    return arr * w


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_signal(params: SignalParameters) -> SignalData:
    """Generate a synthetic time-domain signal from *params*.

    Parameters
    ----------
    params:
        Validated ``SignalParameters`` instance.

    Returns
    -------
    SignalData
        Arrays for time, clean signal, noise, and composite waveform.
    """
    n_samples = int(params.duration * params.sampling_rate)
    t = np.linspace(0.0, params.duration, n_samples, endpoint=False)
    omega = 2.0 * np.pi * params.frequency
    phase_rad = np.deg2rad(params.phase_deg)

    match params.signal_type:
        case SignalType.SINE:
            raw = params.amplitude * np.sin(omega * t + phase_rad)

        case SignalType.SQUARE:
            raw = params.amplitude * np.sign(np.sin(omega * t + phase_rad))

        case SignalType.SAWTOOTH:
            # Linearly ramps from -A to +A within each period.
            period = 1.0 / params.frequency
            phase_shift = phase_rad / omega
            raw = params.amplitude * (2.0 * ((t + phase_shift) % period) / period - 1.0)

        case SignalType.TRIANGLE:
            period = 1.0 / params.frequency
            phase_shift = phase_rad / omega
            raw = params.amplitude * (
                2.0 * np.abs(2.0 * ((t + phase_shift) % period) / period - 1.0) - 1.0
            )

        case SignalType.WHITE_NOISE:
            rng = np.random.default_rng()
            raw = params.amplitude * rng.standard_normal(n_samples)

        case _:
            raw = np.zeros(n_samples)

    # ------------------------------------------------------------------
    # Additive noise
    # ------------------------------------------------------------------
    noise = np.zeros(n_samples)
    if params.noise_type != NoiseType.NONE:
        signal_power = float(np.mean(raw**2))
        if signal_power > 0.0:
            noise_power = signal_power / (10.0 ** (params.snr_db / 10.0))
            noise_std = float(np.sqrt(noise_power))
            rng = np.random.default_rng()
            if params.noise_type == NoiseType.GAUSSIAN:
                noise = rng.normal(0.0, noise_std, n_samples)
            else:  # UNIFORM — same variance as Gaussian for given SNR
                bound = noise_std * float(np.sqrt(3.0))
                noise = rng.uniform(-bound, bound, n_samples)

    composite = raw + noise + params.dc_offset

    logger.debug(
        "Signal generated",
        extra={"n_samples": n_samples, "signal_type": params.signal_type},
    )
    return SignalData(
        time=t,
        signal=raw,
        noise=noise,
        composite=composite,
        sample_rate=params.sampling_rate,
    )


def compute_fft(signal_data: SignalData, params: SignalParameters) -> FFTResult:
    """Compute the FFT of the composite signal.

    Only the first ``params.fft_size`` samples are used so the window length
    is always a power of two (as validated by ``SignalParameters``).

    Parameters
    ----------
    signal_data:
        Time-domain data returned by ``generate_signal``.
    params:
        The same parameter set used to generate the signal (provides
        ``fft_size``, ``fft_window``, and ``sampling_rate``).

    Returns
    -------
    FFTResult
        Positive-frequency bins with magnitude (dB) and phase (degrees).
    """
    segment = signal_data.composite[: params.fft_size]
    windowed = _apply_window(segment, params.fft_window)

    spectrum = np.fft.rfft(windowed)
    frequencies = np.fft.rfftfreq(params.fft_size, d=1.0 / signal_data.sample_rate)

    # Normalise so that a full-scale sine reads 0 dB at its fundamental.
    magnitude = np.abs(spectrum) / (params.fft_size / 2.0)
    magnitude = np.where(magnitude < _LOG_FLOOR, _LOG_FLOOR, magnitude)
    magnitude_db = 20.0 * np.log10(magnitude)

    phase_deg = np.rad2deg(np.angle(spectrum))

    logger.debug(
        "FFT computed",
        extra={"fft_size": params.fft_size, "fft_window": params.fft_window},
    )
    return FFTResult(
        frequencies=frequencies,
        magnitude_db=magnitude_db,
        phase_deg=phase_deg,
    )


def compute_metrics(signal_data: SignalData, fft_result: FFTResult) -> SignalMetrics:
    """Derive scalar quality metrics from the computed signal and FFT.

    Parameters
    ----------
    signal_data:
        Time-domain data.
    fft_result:
        Frequency-domain data.

    Returns
    -------
    SignalMetrics
        RMS, peak, crest factor, SNR, THD, and dominant frequency.
    """
    composite = signal_data.composite

    rms = float(np.sqrt(np.mean(composite**2)))
    peak = float(np.max(np.abs(composite)))
    crest_factor = peak / rms if rms > 0.0 else 0.0

    # SNR — only meaningful when noise was added.
    snr_db: float | None = None
    if np.any(signal_data.noise != 0.0):
        signal_power = float(np.mean(signal_data.signal**2))
        noise_power = float(np.mean(signal_data.noise**2))
        if noise_power > 0.0:
            snr_db = 10.0 * np.log10(signal_power / noise_power)

    # THD — ratio of harmonic power (H2–H5) to fundamental power.
    peak_idx = int(np.argmax(fft_result.magnitude_db))
    fund_linear = 10.0 ** (fft_result.magnitude_db[peak_idx] / 20.0)
    fund_power = fund_linear**2

    harmonic_power = 0.0
    for k in range(2, 6):
        h_idx = peak_idx * k
        if h_idx < len(fft_result.magnitude_db):
            h_linear = 10.0 ** (fft_result.magnitude_db[h_idx] / 20.0)
            harmonic_power += h_linear**2

    if harmonic_power > 0.0 and fund_power > 0.0:
        thd_db = 10.0 * np.log10(harmonic_power / fund_power)
    else:
        thd_db = -100.0

    peak_freq = float(fft_result.frequencies[peak_idx]) if len(fft_result.frequencies) > 0 else 0.0

    return SignalMetrics(
        rms=rms,
        peak=peak,
        crest_factor=crest_factor,
        snr_db=snr_db,
        thd_db=thd_db,
        peak_freq=peak_freq,
    )
