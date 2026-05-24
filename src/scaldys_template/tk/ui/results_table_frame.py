"""Results table panel.

``ResultsTableFrame`` displays the computed signal data in a two-tab
``Notebook``:

- **Time Domain** — time, signal, noise, composite (one row per sample,
  downsampled to *max_display_rows* for performance).
- **Frequency Domain** — frequency bin, magnitude (dB), phase (°).

It also exposes a **Metrics** summary bar above the tabs and an
**Export CSV** button that writes the current data to a user-chosen file.
"""

from __future__ import annotations

import csv
import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, CENTER, END, HEADINGS, X, YES

from scaldys_template.__about__ import PACKAGE_NAME
from scaldys_template.core.signal_engine import FFTResult, SignalData, SignalMetrics

__all__ = ["ResultsTableFrame"]

logger = logging.getLogger(PACKAGE_NAME)

# Maximum rows shown in the Time Domain tab (downsampled for speed).
_MAX_DISPLAY_ROWS = 2000


class ResultsTableFrame(ttk.LabelFrame):
    """Tabbed results table.

    Parameters
    ----------
    master:
        Parent widget.
    **kwargs:
        Passed to ``tb.LabelFrame``.
    """

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        kwargs.setdefault("text", "Results")
        super().__init__(master, **kwargs)

        self._signal_data: SignalData | None = None
        self._fft_result: FFTResult | None = None

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # --- Metrics bar ---
        metrics_frame = tb.Frame(self)
        metrics_frame.pack(fill=X, pady=(0, 4))

        self._metric_vars: dict[str, tk.StringVar] = {}
        for label in ("RMS", "Peak", "Crest factor", "SNR (dB)", "THD (dB)", "Peak freq (Hz)"):
            key = label
            self._metric_vars[key] = tk.StringVar(value="—")
            cell = tb.Frame(metrics_frame)
            cell.pack(side="left", padx=6)
            tb.Label(cell, text=label, font="-size 8").pack()
            tb.Label(cell, textvariable=self._metric_vars[key], font="-size 9 -weight bold").pack()

        tb.Separator(self).pack(fill=X, pady=2)

        # --- Export button ---
        export_btn = tb.Button(
            self,
            text="Export CSV…",
            bootstyle="secondary-outline",
            command=self._export_csv,
        )
        export_btn.pack(anchor="e", pady=(0, 4))

        # --- Notebook with two tabs ---
        self._notebook = tb.Notebook(self)
        self._notebook.pack(fill=BOTH, expand=YES)

        # Time domain tab
        td_frame = tb.Frame(self._notebook)
        self._notebook.add(td_frame, text="Time Domain")
        self._td_tree, self._td_scroll = self._build_treeview(
            td_frame,
            columns=("time", "signal", "noise", "composite"),
            headings=("Time (s)", "Signal", "Noise", "Composite"),
            widths=(100, 100, 100, 100),
        )

        # Frequency domain tab
        fd_frame = tb.Frame(self._notebook)
        self._notebook.add(fd_frame, text="Frequency Domain")
        self._fd_tree, self._fd_scroll = self._build_treeview(
            fd_frame,
            columns=("freq", "magnitude", "phase"),
            headings=("Frequency (Hz)", "Magnitude (dB)", "Phase (°)"),
            widths=(130, 130, 110),
        )

    def _build_treeview(
        self,
        parent: tb.Frame,
        columns: tuple[str, ...],
        headings: tuple[str, ...],
        widths: tuple[int, ...],
    ) -> tuple[tb.Treeview, tb.Scrollbar]:
        container = tb.Frame(parent)
        container.pack(fill=BOTH, expand=YES)

        vsb = tb.Scrollbar(container, orient="vertical")
        vsb.pack(side="right", fill="y")

        hsb = tb.Scrollbar(container, orient="horizontal")
        hsb.pack(side="bottom", fill=X)

        tree = tb.Treeview(
            container,
            columns=list(columns),
            show=HEADINGS,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )
        tree.pack(fill=BOTH, expand=YES, side="left")

        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)

        for col, heading, width in zip(columns, headings, widths):
            tree.heading(col, text=heading)
            tree.column(col, width=width, anchor=CENTER, minwidth=60)

        return tree, vsb

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_results(
        self,
        signal_data: SignalData,
        fft_result: FFTResult,
        metrics: SignalMetrics,
    ) -> None:
        """Populate both tables and the metrics bar with new computation results."""
        self._signal_data = signal_data
        self._fft_result = fft_result

        self._update_metrics_bar(metrics)
        self._populate_time_domain(signal_data)
        self._populate_frequency_domain(fft_result)

    def clear(self) -> None:
        """Clear all displayed data."""
        self._signal_data = None
        self._fft_result = None
        for var in self._metric_vars.values():
            var.set("—")
        self._td_tree.delete(*self._td_tree.get_children())
        self._fd_tree.delete(*self._fd_tree.get_children())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_metrics_bar(self, metrics: SignalMetrics) -> None:
        self._metric_vars["RMS"].set(f"{metrics.rms:.4f}")
        self._metric_vars["Peak"].set(f"{metrics.peak:.4f}")
        self._metric_vars["Crest factor"].set(f"{metrics.crest_factor:.3f}")
        self._metric_vars["SNR (dB)"].set(
            f"{metrics.snr_db:.1f}" if metrics.snr_db is not None else "N/A"
        )
        self._metric_vars["THD (dB)"].set(f"{metrics.thd_db:.1f}")
        self._metric_vars["Peak freq (Hz)"].set(f"{metrics.peak_freq:.2f}")

    def _populate_time_domain(self, sd: SignalData) -> None:
        tree = self._td_tree
        tree.delete(*tree.get_children())

        n = len(sd.time)
        step = max(1, n // _MAX_DISPLAY_ROWS)
        indices = range(0, n, step)

        for i in indices:
            tree.insert(
                "",
                "end",
                values=(
                    f"{sd.time[i]:.6f}",
                    f"{sd.signal[i]:.6f}",
                    f"{sd.noise[i]:.6f}",
                    f"{sd.composite[i]:.6f}",
                ),
            )

    def _populate_frequency_domain(self, fft: FFTResult) -> None:
        tree = self._fd_tree
        tree.delete(*tree.get_children())

        for freq, mag, phase in zip(fft.frequencies, fft.magnitude_db, fft.phase_deg):
            tree.insert(
                "",
                "end",
                values=(
                    f"{freq:.3f}",
                    f"{mag:.3f}",
                    f"{phase:.2f}",
                ),
            )

    def _export_csv(self) -> None:
        if self._signal_data is None or self._fft_result is None:
            return

        path_str = filedialog.asksaveasfilename(
            title="Export CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            # Write both domains into a single file (two sections separated by blank line)
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                writer.writerow(["# Time Domain"])
                writer.writerow(["time_s", "signal", "noise", "composite"])
                sd = self._signal_data
                for i in range(len(sd.time)):
                    writer.writerow(
                        [
                            f"{sd.time[i]:.8f}",
                            f"{sd.signal[i]:.8f}",
                            f"{sd.noise[i]:.8f}",
                            f"{sd.composite[i]:.8f}",
                        ]
                    )

                writer.writerow([])
                writer.writerow(["# Frequency Domain"])
                writer.writerow(["frequency_hz", "magnitude_db", "phase_deg"])
                fft = self._fft_result
                for freq, mag, phase in zip(fft.frequencies, fft.magnitude_db, fft.phase_deg):
                    writer.writerow([f"{freq:.4f}", f"{mag:.4f}", f"{phase:.4f}"])

            logger.info("Results exported to %s", path)
        except OSError as exc:
            logger.error("CSV export failed: %s", exc)
            tk.messagebox.showerror("Export Error", str(exc))  # type: ignore[attr-defined]
