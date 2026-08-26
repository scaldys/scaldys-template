"""Signal analyzer parameter model.

Defines the ``SignalParameters`` Pydantic model that drives both the GUI and the
CLI ``analyze`` command.  All field-level and cross-field validation lives here
so it is exercised the same way regardless of how the parameters arrive.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, field_validator, model_validator

__all__ = [
    "MAX_SAMPLES",
    "NoiseType",
    "SignalParameters",
    "SignalType",
    "WindowType",
]

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

MAX_SAMPLES = 10_000_000  # hard ceiling on generated sample count (~40 MB float64)


class SignalType(StrEnum):
    SINE = "sine"
    SQUARE = "square"
    SAWTOOTH = "sawtooth"
    TRIANGLE = "triangle"
    WHITE_NOISE = "white_noise"


class NoiseType(StrEnum):
    NONE = "none"
    GAUSSIAN = "gaussian"
    UNIFORM = "uniform"


class WindowType(StrEnum):
    RECTANGULAR = "rectangular"
    HANNING = "hanning"
    HAMMING = "hamming"
    BLACKMAN = "blackman"


# ---------------------------------------------------------------------------
# Parameter model
# ---------------------------------------------------------------------------


class SignalParameters(BaseModel):
    """All parameters that define a signal analysis run.

    Validation rules
    ----------------
    - ``frequency``: 0.1 – 10 000 Hz
    - ``amplitude``: > 0
    - ``duration``: 0.001 – 60 s
    - ``sampling_rate``: ≥ 2 × frequency  (Nyquist)
    - ``phase_deg``: 0 – 360
    - ``fft_size``: ≥ 2, power of two, ≤ total sample count
    - total samples (duration × sampling_rate) ≤ MAX_SAMPLES
    """

    signal_type: SignalType = SignalType.SINE
    frequency: float = 440.0  # Hz  (A4 — immediately audible and recognisable)
    amplitude: float = 1.0
    duration: float = 0.1  # seconds  (→ 4 410 samples at 44.1 kHz)
    sampling_rate: float = 44100.0  # Hz  (CD-quality standard)
    phase_deg: float = 0.0  # degrees
    dc_offset: float = 0.0
    noise_type: NoiseType = NoiseType.NONE
    snr_db: float = 20.0  # dB — only used when noise_type != NONE
    fft_window: WindowType = WindowType.HANNING
    fft_size: int = 1024  # 1024 ≤ 4 410 samples at default rate/duration

    # ------------------------------------------------------------------
    # Field-level validators
    # ------------------------------------------------------------------

    @field_validator("frequency")
    @classmethod
    def check_frequency(cls, v: float) -> float:
        if not (0.1 <= v <= 10_000.0):
            raise ValueError("Frequency must be between 0.1 and 10 000 Hz.")
        return v

    @field_validator("amplitude")
    @classmethod
    def check_amplitude(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amplitude must be > 0.")
        return v

    @field_validator("duration")
    @classmethod
    def check_duration(cls, v: float) -> float:
        if not (0.001 <= v <= 60.0):
            raise ValueError("Duration must be between 0.001 and 60 s.")
        return v

    @field_validator("sampling_rate")
    @classmethod
    def check_sampling_rate(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Sampling rate must be > 0 Hz.")
        return v

    @field_validator("phase_deg")
    @classmethod
    def check_phase(cls, v: float) -> float:
        if not (0.0 <= v <= 360.0):
            raise ValueError("Phase offset must be between 0 and 360°.")
        return v

    @field_validator("fft_size")
    @classmethod
    def check_fft_size(cls, v: int) -> int:
        if v < 2:
            raise ValueError("FFT size must be ≥ 2.")
        if (v & (v - 1)) != 0:
            raise ValueError("FFT size must be a power of two (e.g. 256, 512, 1024, …).")
        return v

    # ------------------------------------------------------------------
    # Cross-field validator (runs after all field validators)
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def check_cross_constraints(self) -> SignalParameters:
        # Nyquist criterion
        if self.sampling_rate < 2.0 * self.frequency:
            raise ValueError(
                f"Sampling rate ({self.sampling_rate:.1f} Hz) must be ≥ 2× frequency "
                f"({self.frequency:.1f} Hz).  Minimum required: {2 * self.frequency:.1f} Hz."
            )

        total_samples = int(self.duration * self.sampling_rate)

        # Memory guard
        if total_samples > MAX_SAMPLES:
            raise ValueError(
                f"Signal would require {total_samples:,} samples which exceeds the limit "
                f"of {MAX_SAMPLES:,}.  Reduce duration or sampling rate."
            )

        # FFT size cannot exceed the number of generated samples
        if self.fft_size > total_samples:
            raise ValueError(
                f"FFT size ({self.fft_size}) must be ≤ total samples "
                f"({total_samples} = duration × sampling rate)."
            )

        return self
