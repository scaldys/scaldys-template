"""Embedded matplotlib plot panel.

``PlotFrame`` hosts three tab-switched matplotlib figures inside a ttkbootstrap
``LabelFrame``:

- **Time Domain** — composite waveform with signal and noise overlays
- **Spectrum** — FFT magnitude in dB
- **Phase** — FFT phase in degrees

Each tab includes a ``NavigationToolbar2Tk`` giving the user free zoom, pan,
and PNG save without additional code.  Figure and axes colours follow the
active ttkbootstrap theme (dark or light).
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
from typing import Any

import matplotlib
import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, YES

matplotlib.use("TkAgg")  # must be set before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from scaldys_template.__about__ import PACKAGE_NAME
from scaldys_template.core.signal_engine import FFTResult, SignalData
from scaldys_template.core.signal_model import SignalParameters

__all__ = ["PlotFrame"]

logger = logging.getLogger(PACKAGE_NAME)

# Number of time-domain points rendered in the plot (downsampled for speed).
_MAX_PLOT_POINTS = 4000


def _theme_colors() -> tuple[str, str, str, str]:
    """Return (fig_bg, axes_bg, fg, grid) colours matching the active theme.

    Returns
    -------
    tuple of str
        ``(fig_bg, axes_bg, fg_color, grid_color)``
    """
    style = tb.Style()
    theme = style.theme
    assert theme is not None
    if theme.type == "dark":
        fig_bg = "#1e1e2e"
        axes_bg = "#2a2a3e"
        fg = "#e0e0e0"
        grid = "#444466"
    else:
        fig_bg = "#f8f8f8"
        axes_bg = "#ffffff"
        fg = "#222222"
        grid = "#cccccc"
    return fig_bg, axes_bg, fg, grid


def _apply_theme(fig: Figure, axes: list[Any]) -> None:
    """Apply ttkbootstrap theme colours to a matplotlib figure."""
    fig_bg, axes_bg, fg, grid = _theme_colors()
    fig.patch.set_facecolor(fig_bg)
    for ax in axes:
        ax.set_facecolor(axes_bg)
        ax.tick_params(colors=fg, labelsize=8)
        ax.xaxis.label.set_color(fg)
        ax.yaxis.label.set_color(fg)
        ax.title.set_color(fg)
        ax.spines[:].set_edgecolor(fg)
        ax.grid(True, color=grid, linestyle="--", linewidth=0.5, alpha=0.7)


class _PlotTab(tb.Frame):
    """One tab containing a single matplotlib figure + navigation toolbar."""

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.fig, self.ax = plt.subplots(figsize=(6, 3.5))
        self.fig.tight_layout(pad=2.0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=YES)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(fill=tk.X, side=tk.BOTTOM)

    def redraw(self) -> None:
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw_idle()


class PlotFrame(ttk.LabelFrame):
    """Three-tab plot panel embedding matplotlib figures.

    Parameters
    ----------
    master:
        Parent widget.
    **kwargs:
        Passed to ``tb.LabelFrame``.
    """

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        kwargs.setdefault("text", "Plots")
        super().__init__(master, **kwargs)

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self._notebook = tb.Notebook(self)
        self._notebook.pack(fill=BOTH, expand=YES)

        self._time_tab = _PlotTab(self._notebook)
        self._spectrum_tab = _PlotTab(self._notebook)
        self._phase_tab = _PlotTab(self._notebook)

        self._notebook.add(self._time_tab, text="Time Domain")
        self._notebook.add(self._spectrum_tab, text="Spectrum")
        self._notebook.add(self._phase_tab, text="Phase")

        # Draw empty placeholder axes immediately so the panel looks intentional.
        self._draw_empty_plots()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_plots(
        self,
        signal_data: SignalData,
        fft_result: FFTResult,
        params: SignalParameters,
    ) -> None:
        """Redraw all three plots from new computation results."""
        self._draw_time_domain(signal_data, params)
        self._draw_spectrum(fft_result, params)
        self._draw_phase(fft_result)

    def clear(self) -> None:
        """Reset all plots to their empty placeholder state."""
        self._draw_empty_plots()

    # ------------------------------------------------------------------
    # Plot builders
    # ------------------------------------------------------------------

    def _draw_empty_plots(self) -> None:
        for tab, title in (
            (self._time_tab, "Time Domain — run analysis to populate"),
            (self._spectrum_tab, "Spectrum — run analysis to populate"),
            (self._phase_tab, "Phase — run analysis to populate"),
        ):
            ax = tab.ax
            ax.cla()
            ax.set_title(title, fontsize=9)
            _apply_theme(tab.fig, [ax])
            tab.redraw()

    def _draw_time_domain(self, sd: SignalData, params: SignalParameters) -> None:
        tab = self._time_tab
        ax = tab.ax
        ax.cla()

        n = len(sd.time)
        step = max(1, n // _MAX_PLOT_POINTS)
        t = sd.time[::step]
        composite = sd.composite[::step]
        signal = sd.signal[::step]

        _, _, fg, _ = _theme_colors()

        ax.plot(t, composite, color="#4db6e8", linewidth=0.9, label="Composite", zorder=3)
        if sd.noise.any():
            noise_vis = sd.noise[::step]
            ax.plot(
                t,
                signal,
                color="#a8d8a8",
                linewidth=0.7,
                linestyle="--",
                label="Signal",
                zorder=2,
                alpha=0.8,
            )
            ax.plot(
                t,
                noise_vis,
                color="#f4a261",
                linewidth=0.6,
                linestyle=":",
                label="Noise",
                zorder=1,
                alpha=0.7,
            )

        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Amplitude", fontsize=8)
        ax.set_title(
            f"{params.signal_type.capitalize()}  {params.frequency:.1f} Hz  "
            f"A={params.amplitude:.3g}  fs={params.sampling_rate:.0f} Hz",
            fontsize=9,
        )
        if sd.noise.any():
            legend = ax.legend(fontsize=7, framealpha=0.3)
            for text in legend.get_texts():
                text.set_color(fg)

        _apply_theme(tab.fig, [ax])
        tab.redraw()
        logger.debug("Time-domain plot updated")

    def _draw_spectrum(self, fft: FFTResult, params: SignalParameters) -> None:
        tab = self._spectrum_tab
        ax = tab.ax
        ax.cla()

        ax.plot(fft.frequencies, fft.magnitude_db, color="#a78bfa", linewidth=0.9)
        ax.set_xlabel("Frequency (Hz)", fontsize=8)
        ax.set_ylabel("Magnitude (dB)", fontsize=8)
        ax.set_title(
            f"FFT Magnitude — {params.fft_size}-pt {params.fft_window.capitalize()} window",
            fontsize=9,
        )
        ax.set_xlim(left=0, right=fft.frequencies[-1] if len(fft.frequencies) else 1)

        _apply_theme(tab.fig, [ax])
        tab.redraw()
        logger.debug("Spectrum plot updated")

    def _draw_phase(self, fft: FFTResult) -> None:
        tab = self._phase_tab
        ax = tab.ax
        ax.cla()

        ax.plot(fft.frequencies, fft.phase_deg, color="#f9a8d4", linewidth=0.8, alpha=0.85)
        ax.set_xlabel("Frequency (Hz)", fontsize=8)
        ax.set_ylabel("Phase (°)", fontsize=8)
        ax.set_title("FFT Phase", fontsize=9)
        ax.set_xlim(left=0, right=fft.frequencies[-1] if len(fft.frequencies) else 1)
        ax.set_ylim(-185, 185)
        ax.axhline(0, color="#888888", linewidth=0.6, linestyle="--")

        _apply_theme(tab.fig, [ax])
        tab.redraw()
        logger.debug("Phase plot updated")
