"""Signal parameter panel.

``SignalParametersFrame`` renders all ``SignalParameters`` fields as labeled
input widgets inside a scrollable ttkbootstrap ``LabelFrame``.  It provides:

- ``get_parameters()`` — validate and return a ``SignalParameters`` or ``None``
- ``set_parameters(params)`` — populate all widgets from a model instance
- Live per-field validation on focus-out (red border + tooltip message)
- Automatic enable/disable of the SNR field based on noise type
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import (
    BOTH,
    DANGER,
    W,
    X,
    YES,
)  # BOTH, DANGER, END, LEFT, RIGHT, W, X, YES
from pydantic import ValidationError

from scaldys_template.core.signal_model import (
    NoiseType,
    SignalParameters,
    SignalType,
    WindowType,
)

__all__ = ["SignalParametersFrame"]

# Human-readable display labels for each enum (preserves definition order)
_SIGNAL_TYPE_LABELS: list[str] = ["Sine", "Square", "Sawtooth", "Triangle", "White Noise"]
_SIGNAL_TYPE_VALUES: list[SignalType] = list(SignalType)

_NOISE_TYPE_LABELS: list[str] = ["None", "Gaussian", "Uniform"]
_NOISE_TYPE_VALUES: list[NoiseType] = list(NoiseType)

_WINDOW_TYPE_LABELS: list[str] = ["Rectangular", "Hanning", "Hamming", "Blackman"]
_WINDOW_TYPE_VALUES: list[WindowType] = list(WindowType)


class SignalParametersFrame(ttk.LabelFrame):
    """Parameter entry panel backed by ``SignalParameters``.

    Parameters
    ----------
    master:
        Parent widget.
    on_change:
        Optional callback invoked when the user finishes editing a field
        (on ``FocusOut`` for numeric widgets, on ``<<ComboboxSelected>>`` for
        dropdowns).  The argument is the current ``SignalParameters`` if all
        fields are valid, or ``None`` if the current state is invalid.  The
        callback is **not** triggered by programmatic calls to
        ``set_parameters()``.
    **kwargs:
        Passed to ``tb.LabelFrame``.
    """

    def __init__(
        self,
        master: tk.Misc,
        on_change: Callable[[SignalParameters | None], None] | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("text", "Signal Parameters")
        super().__init__(master, **kwargs)

        self._on_change = on_change
        self._vars: dict[str, tk.Variable] = {}
        self._widgets: dict[str, Any] = {}
        self._error_labels: dict[str, tb.Label] = {}

        self._build()
        self._bind_events()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # tb.LabelFrame is backed by tk.LabelFrame which does not support
        # -padding, so we apply inner padding here on the content frame instead.
        outer = tb.Frame(self, padding=8)
        outer.pack(fill=BOTH, expand=YES)

        # Two-column grid: label (col 0) + widget (col 1)
        outer.columnconfigure(1, weight=1)

        row = 0

        # --- Signal type ---
        self._add_label(outer, row, "Signal type")
        self._vars["signal_type"] = tk.StringVar(value=_SIGNAL_TYPE_LABELS[0])
        cbo = tb.Combobox(
            outer,
            textvariable=self._vars["signal_type"],
            values=_SIGNAL_TYPE_LABELS,
            state="readonly",
            width=16,
        )
        cbo.grid(row=row, column=1, sticky="ew", pady=2)
        self._widgets["signal_type"] = cbo
        row += 1

        # --- Frequency ---
        row = self._add_float_row(outer, row, "frequency", "Frequency (Hz)", 0.1, 10000.0)

        # --- Amplitude ---
        row = self._add_float_row(outer, row, "amplitude", "Amplitude", 1e-6, 1e6)

        # --- Duration ---
        row = self._add_float_row(outer, row, "duration", "Duration (s)", 0.001, 60.0)

        # --- Sampling rate ---
        row = self._add_float_row(outer, row, "sampling_rate", "Sampling rate (Hz)", 0.1, 1e7)

        # --- Phase ---
        row = self._add_float_row(outer, row, "phase_deg", "Phase offset (°)", 0.0, 360.0)

        # --- DC offset ---
        row = self._add_float_row(outer, row, "dc_offset", "DC offset", -1e6, 1e6)

        tb.Separator(outer).grid(row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        # --- Noise type ---
        self._add_label(outer, row, "Noise type")
        self._vars["noise_type"] = tk.StringVar(value=_NOISE_TYPE_LABELS[0])
        noise_cbo = tb.Combobox(
            outer,
            textvariable=self._vars["noise_type"],
            values=_NOISE_TYPE_LABELS,
            state="readonly",
            width=16,
        )
        noise_cbo.grid(row=row, column=1, sticky="ew", pady=2)
        self._widgets["noise_type"] = noise_cbo
        row += 1

        # --- SNR ---
        row = self._add_float_row(outer, row, "snr_db", "Noise SNR (dB)", -100.0, 200.0)

        tb.Separator(outer).grid(row=row, column=0, columnspan=2, sticky="ew", pady=6)
        row += 1

        # --- FFT window ---
        self._add_label(outer, row, "FFT window")
        # Default index 1 = Hanning, matching SignalParameters default
        self._vars["fft_window"] = tk.StringVar(value=_WINDOW_TYPE_LABELS[1])
        window_cbo = tb.Combobox(
            outer,
            textvariable=self._vars["fft_window"],
            values=_WINDOW_TYPE_LABELS,
            state="readonly",
            width=16,
        )
        window_cbo.grid(row=row, column=1, sticky="ew", pady=2)
        self._widgets["fft_window"] = window_cbo
        row += 1

        # --- FFT size ---
        self._add_label(outer, row, "FFT size")
        self._vars["fft_size"] = tk.StringVar(value="1024")
        fft_entry = tb.Entry(outer, textvariable=self._vars["fft_size"], width=18)
        fft_entry.grid(row=row, column=1, sticky="ew", pady=2)
        self._widgets["fft_size"] = fft_entry
        row += 1

        # Validation error label (shared, shown below the grid)
        self._status_var = tk.StringVar()
        self._status_label = tb.Label(
            self, textvariable=self._status_var, bootstyle=DANGER, wraplength=230
        )
        self._status_label.pack(fill=X, pady=(6, 0))

    def _add_label(self, parent: tb.Frame, row: int, text: str) -> None:
        tb.Label(parent, text=text, anchor=W).grid(row=row, column=0, sticky=W, padx=(0, 8), pady=2)

    def _add_float_row(
        self,
        parent: tb.Frame,
        row: int,
        field: str,
        label: str,
        from_: float,
        to: float,
    ) -> int:
        self._add_label(parent, row, label)
        var = tk.StringVar()
        self._vars[field] = var
        spin = tb.Spinbox(parent, textvariable=var, from_=from_, to=to, increment=1.0, width=18)
        spin.grid(row=row, column=1, sticky="ew", pady=2)
        self._widgets[field] = spin
        return row + 1

    # ------------------------------------------------------------------
    # Events & validation
    # ------------------------------------------------------------------

    def _bind_events(self) -> None:
        # Noise-type change → enable/disable SNR field
        self._vars["noise_type"].trace_add("write", self._on_noise_type_changed)
        self._on_noise_type_changed()  # apply initial state

        # Validate float/int fields on focus-out and notify change callback
        for field in (
            "frequency",
            "amplitude",
            "duration",
            "sampling_rate",
            "phase_deg",
            "dc_offset",
            "snr_db",
            "fft_size",
        ):
            widget = self._widgets[field]
            widget.bind("<FocusOut>", lambda _e, f=field: self._on_field_focusout(f))

        # Combobox selections are instant — notify change immediately
        for field in ("signal_type", "noise_type", "fft_window"):
            self._widgets[field].bind("<<ComboboxSelected>>", lambda _e: self._notify_change())

    def _on_noise_type_changed(self, *_: Any) -> None:
        label = self._vars["noise_type"].get()
        noise = _NOISE_TYPE_VALUES[_NOISE_TYPE_LABELS.index(label)]
        state = "normal" if noise != NoiseType.NONE else "disabled"
        self._widgets["snr_db"].configure(state=state)

    def _on_field_focusout(self, field: str) -> None:
        """Validate *field* and notify the change callback (silent parse)."""
        self._validate_field(field)
        self._notify_change()

    def _notify_change(self) -> None:
        """Fire ``on_change`` with the current (silently parsed) parameters."""
        if self._on_change is not None:
            self._on_change(self._parse_parameters())

    def _parse_parameters(self) -> SignalParameters | None:
        """Parse current widget state silently without updating the UI."""
        try:
            signal_type = _SIGNAL_TYPE_VALUES[
                _SIGNAL_TYPE_LABELS.index(self._vars["signal_type"].get())
            ]
            noise_type = _NOISE_TYPE_VALUES[
                _NOISE_TYPE_LABELS.index(self._vars["noise_type"].get())
            ]
            fft_window = _WINDOW_TYPE_VALUES[
                _WINDOW_TYPE_LABELS.index(self._vars["fft_window"].get())
            ]
            return SignalParameters(
                signal_type=signal_type,
                frequency=float(self._vars["frequency"].get()),
                amplitude=float(self._vars["amplitude"].get()),
                duration=float(self._vars["duration"].get()),
                sampling_rate=float(self._vars["sampling_rate"].get()),
                phase_deg=float(self._vars["phase_deg"].get()),
                dc_offset=float(self._vars["dc_offset"].get()),
                noise_type=noise_type,
                snr_db=float(self._vars["snr_db"].get()),
                fft_window=fft_window,
                fft_size=int(self._vars["fft_size"].get()),
            )
        except (ValueError, IndexError, ValidationError):
            return None

    def _validate_field(self, field: str) -> bool:
        """Validate a single field in isolation.  Returns True if valid."""
        raw = self._vars[field].get().strip()
        widget = self._widgets[field]
        try:
            if field == "fft_size":
                val = int(raw)
                if (val & (val - 1)) != 0 or val < 2:
                    raise ValueError("Must be a power of 2 and ≥ 2.")
            else:
                float(raw)
            widget.configure(bootstyle="")
            return True
        except (ValueError, tk.TclError):
            widget.configure(bootstyle=DANGER)
            return False

    def _clear_status(self) -> None:
        self._status_var.set("")
        for field in self._widgets:
            try:
                self._widgets[field].configure(bootstyle="")
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_parameters(self) -> SignalParameters | None:
        """Read all widgets, validate, and return a ``SignalParameters``.

        Returns ``None`` and shows an error message if validation fails.
        """
        self._clear_status()

        # Gather raw values
        try:
            signal_label = self._vars["signal_type"].get()
            signal_type = _SIGNAL_TYPE_VALUES[_SIGNAL_TYPE_LABELS.index(signal_label)]

            noise_label = self._vars["noise_type"].get()
            noise_type = _NOISE_TYPE_VALUES[_NOISE_TYPE_LABELS.index(noise_label)]

            window_label = self._vars["fft_window"].get()
            fft_window = _WINDOW_TYPE_VALUES[_WINDOW_TYPE_LABELS.index(window_label)]

            raw = {
                "signal_type": signal_type,
                "frequency": float(self._vars["frequency"].get()),
                "amplitude": float(self._vars["amplitude"].get()),
                "duration": float(self._vars["duration"].get()),
                "sampling_rate": float(self._vars["sampling_rate"].get()),
                "phase_deg": float(self._vars["phase_deg"].get()),
                "dc_offset": float(self._vars["dc_offset"].get()),
                "noise_type": noise_type,
                "snr_db": float(self._vars["snr_db"].get()),
                "fft_window": fft_window,
                "fft_size": int(self._vars["fft_size"].get()),
            }
        except (ValueError, IndexError) as exc:
            self._status_var.set(f"Input error: {exc}")
            return None

        try:
            params = SignalParameters(**raw)
        except ValidationError as exc:
            # Show the first error message; highlight the offending widget if possible.
            first = exc.errors()[0]
            msg = first.get("msg", str(exc))
            # Strip Pydantic's "Value error, " prefix when present
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, ") :]
            self._status_var.set(msg)
            # Attempt to highlight the field
            loc = first.get("loc", ())
            if loc:
                field_name = str(loc[-1])
                if field_name in self._widgets:
                    self._widgets[field_name].configure(bootstyle=DANGER)
            return None

        return params

    def set_parameters(self, params: SignalParameters) -> None:
        """Populate all widgets from *params*."""
        self._clear_status()

        idx = _SIGNAL_TYPE_VALUES.index(params.signal_type)
        self._vars["signal_type"].set(_SIGNAL_TYPE_LABELS[idx])

        self._vars["frequency"].set(str(params.frequency))
        self._vars["amplitude"].set(str(params.amplitude))
        self._vars["duration"].set(str(params.duration))
        self._vars["sampling_rate"].set(str(params.sampling_rate))
        self._vars["phase_deg"].set(str(params.phase_deg))
        self._vars["dc_offset"].set(str(params.dc_offset))

        n_idx = _NOISE_TYPE_VALUES.index(params.noise_type)
        self._vars["noise_type"].set(_NOISE_TYPE_LABELS[n_idx])

        self._vars["snr_db"].set(str(params.snr_db))

        w_idx = _WINDOW_TYPE_VALUES.index(params.fft_window)
        self._vars["fft_window"].set(_WINDOW_TYPE_LABELS[w_idx])

        self._vars["fft_size"].set(str(params.fft_size))

        self._on_noise_type_changed()
