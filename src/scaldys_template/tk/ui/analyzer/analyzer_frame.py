"""Main Signal Analyzer layout frame.

``AnalyzerFrame`` is the top-level content widget for the signal analyzer.
It wires together the three sub-frames into a two-column layout:

    ┌─────────────────────┬──────────────────────────────────────────────┐
    │  SignalParameters   │  PlotFrame (tabs: Time / Spectrum / Phase)   │
    │  Frame              │                                              │
    │                     ├──────────────────────────────────────────────┤
    │  [Run] [Save] [Load]│  ResultsTableFrame (Time / Freq tabs)        │
    └─────────────────────┴──────────────────────────────────────────────┘

Run is executed in a background ``threading.Thread`` so the UI remains
responsive.  A ``queue.Queue`` is used to pass results back to the main
thread; ``tk.after()`` polls the queue at 100 ms intervals.
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Literal

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, LEFT, X, YES  # BOTH, BOTTOM, LEFT, RIGHT, TOP, X, YES

from scaldys_template.__about__ import PACKAGE_NAME
from scaldys_template.core.parameter_store import load_parameters, save_parameters
from scaldys_template.core.signal_engine import (
    FFTResult,
    SignalData,
    SignalMetrics,
    compute_fft,
    compute_metrics,
    generate_signal,
)
from scaldys_template.core.signal_model import SignalParameters
from scaldys_template.tk.ui.analyzer.plot_frame import PlotFrame
from scaldys_template.tk.ui.analyzer.results_table_frame import ResultsTableFrame
from scaldys_template.tk.ui.analyzer.signal_parameters_frame import SignalParametersFrame

__all__ = ["AnalyzerFrame"]

logger = logging.getLogger(PACKAGE_NAME)

# Result queue item types
_ResultOk = tuple[Literal["ok"], SignalData, FFTResult, SignalMetrics, SignalParameters]
_ResultErr = tuple[Literal["error"], str]


class AnalyzerFrame(tb.Frame):
    """Top-level signal analyzer content frame.

    Parameters
    ----------
    master:
        Parent widget (typically the ``Application`` window content area).
    **kwargs:
        Passed to ``tb.Frame``.
    """

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._result_queue: queue.Queue[_ResultOk | _ResultErr] = queue.Queue()
        self._is_running = False
        self._last_params: SignalParameters | None = None
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # ── Left column: parameters + action buttons ──────────────────
        left = tb.Frame(self, padding=(6, 6, 3, 6))
        left.pack(side=LEFT, fill="y")

        self._params_frame = SignalParametersFrame(left)
        self._params_frame.pack(fill=X)
        # Populate defaults
        self._params_frame.set_parameters(SignalParameters())

        self._build_action_buttons(left)

        # Vertical separator
        tb.Separator(self, orient="vertical").pack(side=LEFT, fill="y", padx=2)

        # ── Right column: plots (top) + table (bottom) ─────────────────
        right = tb.Frame(self, padding=(3, 6, 6, 6))
        right.pack(side=LEFT, fill=BOTH, expand=YES)

        # PanedWindow so the user can resize vertically
        paned = tk.PanedWindow(right, orient="vertical", sashrelief="raised", sashwidth=5)
        paned.pack(fill=BOTH, expand=YES)

        self._plot_frame = PlotFrame(paned)
        self._table_frame = ResultsTableFrame(paned)

        paned.add(self._plot_frame, stretch="always")
        paned.add(self._table_frame, stretch="always")

        # Give ~60 % of vertical space to plots on first render
        self.after(100, lambda: paned.sash_place(0, 0, int(paned.winfo_height() * 0.6) or 360))

    def _build_action_buttons(self, parent: tb.Frame) -> None:
        btn_frame = tb.Frame(parent, padding=(0, 8, 0, 0))
        btn_frame.pack(fill=X)

        self._run_btn = tb.Button(
            btn_frame,
            text="▶  Run",
            bootstyle="success",
            command=self._on_run,
        )
        self._run_btn.pack(fill=X, pady=(0, 4))

        self._progress = tb.Progressbar(
            btn_frame, mode="indeterminate", bootstyle="success-striped"
        )
        self._progress.pack(fill=X, pady=(0, 6))

        save_btn = tb.Button(
            btn_frame,
            text="Save parameters…",
            bootstyle="secondary-outline",
            command=self._on_save,
        )
        save_btn.pack(fill=X, pady=2)

        load_btn = tb.Button(
            btn_frame,
            text="Load parameters…",
            bootstyle="secondary-outline",
            command=self._on_load,
        )
        load_btn.pack(fill=X, pady=2)

        tb.Separator(btn_frame).pack(fill=X, pady=6)

        reset_btn = tb.Button(
            btn_frame,
            text="Reset to defaults",
            bootstyle="warning-outline",
            command=self._on_reset,
        )
        reset_btn.pack(fill=X)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _on_run(self) -> None:
        if self._is_running:
            return

        params = self._params_frame.get_parameters()
        if params is None:
            return  # validation failed — error already shown in params frame

        self._last_params = params
        self._is_running = True
        self._run_btn.configure(state="disabled")
        self._progress.start(10)
        logger.info("Analysis started", extra={"signal_type": params.signal_type})

        def _worker() -> None:
            try:
                sd = generate_signal(params)
                fft = compute_fft(sd, params)
                mtr = compute_metrics(sd, fft)
                self._result_queue.put(("ok", sd, fft, mtr, params))
            except Exception as exc:  # noqa: BLE001
                self._result_queue.put(("error", str(exc)))

        threading.Thread(target=_worker, daemon=True, name="signal-engine").start()
        self.after(100, self._poll_result)

    def _poll_result(self) -> None:
        try:
            item = self._result_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_result)
            return

        self._progress.stop()
        self._is_running = False
        self._run_btn.configure(state="normal")

        if item[0] == "ok":
            _, sd, fft, mtr, params = item  # type: ignore[misc]
            self._table_frame.update_results(sd, fft, mtr)
            self._plot_frame.update_plots(sd, fft, params)
            logger.info("Analysis complete")
        else:
            msg = item[1]  # type: ignore[index]
            logger.error("Analysis failed: %s", msg)
            messagebox.showerror("Analysis Error", msg)

    def _on_save(self) -> None:
        path_str = filedialog.asksaveasfilename(
            title="Save Parameters",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path_str:
            return
        params = self._params_frame.get_parameters()
        if params is None:
            return
        try:
            save_parameters(params, Path(path_str))
        except OSError as exc:
            messagebox.showerror("Save Error", str(exc))

    def _on_load(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Load Parameters",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path_str:
            return
        try:
            params = load_parameters(Path(path_str))
            self._params_frame.set_parameters(params)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Load Error", str(exc))

    def _on_reset(self) -> None:
        self._params_frame.set_parameters(SignalParameters())
        self._table_frame.clear()
        self._plot_frame.clear()

    def set_parameters(self, params: SignalParameters) -> None:
        """Update the UI with new signal parameters.

        Parameters
        ----------
        params : SignalParameters
            The parameters to load into the UI.
        """
        self._params_frame.set_parameters(params)
