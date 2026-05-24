# -*- coding: utf-8 -*-
# cython: language_level=3

"""
``analyze`` CLI command — headless signal analysis.

Reads ``SignalParameters`` from a JSON file (or uses built-in defaults),
runs the signal engine, and writes results to a directory as CSV files and
PNG plots.

Invocation examples
--------------------
    scaldys-template analyze                           # use default parameters
    scaldys-template analyze params.json               # load from file
    scaldys-template analyze params.json --output ./results
    scaldys-template analyze params.json --output ./results --force
    scaldys-template --log debug analyze params.json
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from scaldys_template.__about__ import APP_NAME, PACKAGE_NAME, VERSION
from scaldys_template.common.app_location import AppLocation
from scaldys_template.core.parameter_store import load_parameters
from scaldys_template.core.signal_engine import (
    compute_fft,
    compute_metrics,
    generate_signal,
)
from scaldys_template.core.signal_model import SignalParameters

__all__ = ["analyze"]

logger = logging.getLogger(PACKAGE_NAME)
console = Console()
err_console = Console(stderr=True)

# ---------------------------------------------------------------------------
# Argument type definitions
# ---------------------------------------------------------------------------

ARG_TYPE_PARAMS_FILE = Annotated[
    Path | None,
    typer.Argument(
        help="Path to a JSON file containing SignalParameters.  Omit to use built-in defaults.",
    ),
]

ARG_TYPE_OUTPUT_DIR = Annotated[
    Path | None,
    typer.Option(
        "--output",
        "-o",
        help="Directory for output files (CSV + PNG).  Defaults to <app_data>/analyze_output.",
    ),
]

ARG_TYPE_FORCE = Annotated[
    bool,
    typer.Option(
        "--force",
        "-f",
        help="Overwrite existing output directory.",
    ),
]

ARG_TYPE_NO_PLOTS = Annotated[
    bool,
    typer.Option(
        "--no-plots",
        help="Skip PNG plot generation (useful in headless / CI environments).",
    ),
]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def analyze(
    ctx: typer.Context,
    params_file: ARG_TYPE_PARAMS_FILE = None,
    output_dir: ARG_TYPE_OUTPUT_DIR = None,
    force: ARG_TYPE_FORCE = False,
    no_plots: ARG_TYPE_NO_PLOTS = False,
) -> None:
    """
    Run headless signal analysis and export results to CSV and PNG.

    Demonstrates:
      - Loading ``SignalParameters`` from JSON (or using defaults)
      - Calling the signal engine from a CLI command
      - Writing tabular results as CSV
      - Saving matplotlib plots as PNG without a display
    """
    logger.info("Starting %s %s — analyze command", APP_NAME, VERSION)

    # ------------------------------------------------------------------
    # Resolve parameters
    # ------------------------------------------------------------------
    if params_file is not None:
        console.print(f"Loading parameters from [cyan]{params_file}[/cyan]…")
        try:
            params = load_parameters(params_file)
        except Exception as exc:
            err_console.print(
                Panel(
                    f"[red]Failed to load parameters:[/red]\n{exc}",
                    title="[bold red]Error[/bold red]",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from exc
    else:
        console.print("No parameters file specified — using built-in defaults.")
        params = SignalParameters()

    # ------------------------------------------------------------------
    # Resolve output directory
    # ------------------------------------------------------------------
    if output_dir is None:
        output_dir = AppLocation.get_directory(AppLocation.AppDataDir) / "analyze_output"

    if output_dir.exists() and not force:
        err_console.print(
            Panel(
                f"Output directory already exists:\n[cyan]{output_dir.resolve()}[/cyan]\n\n"
                "Use [bold]--force[/bold] to overwrite.",
                title="[bold red]Error[/bold red]",
                border_style="red",
                expand=False,
            )
        )
        raise typer.Exit(code=1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Run the signal engine
    # ------------------------------------------------------------------
    console.print("\nRunning signal engine…")
    try:
        signal_data = generate_signal(params)
        fft_result = compute_fft(signal_data, params)
        metrics = compute_metrics(signal_data, fft_result)
    except Exception as exc:
        err_console.print(Panel(f"[red]Signal engine error:[/red]\n{exc}", border_style="red"))
        raise typer.Exit(code=1) from exc

    # ------------------------------------------------------------------
    # Write CSV: time domain
    # ------------------------------------------------------------------
    import csv

    td_path = output_dir / "time_domain.csv"
    with td_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "signal", "noise", "composite"])
        for i in range(len(signal_data.time)):
            writer.writerow(
                [
                    f"{signal_data.time[i]:.8f}",
                    f"{signal_data.signal[i]:.8f}",
                    f"{signal_data.noise[i]:.8f}",
                    f"{signal_data.composite[i]:.8f}",
                ]
            )
    console.print(f"  Time domain  → [cyan]{td_path}[/cyan]")

    # Write CSV: frequency domain
    fd_path = output_dir / "frequency_domain.csv"
    with fd_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["frequency_hz", "magnitude_db", "phase_deg"])
        for freq, mag, phase in zip(
            fft_result.frequencies, fft_result.magnitude_db, fft_result.phase_deg
        ):
            writer.writerow([f"{freq:.4f}", f"{mag:.4f}", f"{phase:.4f}"])
    console.print(f"  Freq domain  → [cyan]{fd_path}[/cyan]")

    # Write CSV: metrics
    mtr_path = output_dir / "metrics.csv"
    with mtr_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["rms", f"{metrics.rms:.6f}"])
        writer.writerow(["peak", f"{metrics.peak:.6f}"])
        writer.writerow(["crest_factor", f"{metrics.crest_factor:.4f}"])
        writer.writerow(
            ["snr_db", f"{metrics.snr_db:.2f}" if metrics.snr_db is not None else "N/A"]
        )
        writer.writerow(["thd_db", f"{metrics.thd_db:.2f}"])
        writer.writerow(["peak_freq_hz", f"{metrics.peak_freq:.4f}"])
    console.print(f"  Metrics      → [cyan]{mtr_path}[/cyan]")

    # ------------------------------------------------------------------
    # Write PNG plots
    # ------------------------------------------------------------------
    if not no_plots:
        _save_plots(signal_data, fft_result, params, output_dir)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    _print_summary(params, metrics, output_dir)

    logger.info("Analyze command finished, output in %s", output_dir)


def _save_plots(signal_data: Any, fft_result: Any, params: Any, output_dir: Path) -> None:  # type: ignore[type-arg]
    """Save the three analysis plots as PNG files."""
    import matplotlib

    matplotlib.use("Agg")  # headless / non-interactive backend
    import matplotlib.pyplot as plt

    n = len(signal_data.time)
    step = max(1, n // 4000)
    t = signal_data.time[::step]
    composite = signal_data.composite[::step]

    # Time domain
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, composite, linewidth=0.8, label="Composite")
    if signal_data.noise.any():
        ax.plot(
            t, signal_data.signal[::step], linewidth=0.6, linestyle="--", label="Signal", alpha=0.7
        )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title(f"{params.signal_type} {params.frequency:.1f} Hz — Time Domain")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    td_png = output_dir / "time_domain.png"
    fig.savefig(td_png, dpi=150)
    plt.close(fig)
    console.print(f"  Time plot    → [cyan]{td_png}[/cyan]")

    # Spectrum
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(fft_result.frequencies, fft_result.magnitude_db, linewidth=0.8)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dB)")
    ax.set_title(f"FFT Spectrum — {params.fft_size}-pt {params.fft_window} window")
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    sp_png = output_dir / "spectrum.png"
    fig.savefig(sp_png, dpi=150)
    plt.close(fig)
    console.print(f"  Spectrum     → [cyan]{sp_png}[/cyan]")

    # Phase
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(fft_result.frequencies, fft_result.phase_deg, linewidth=0.6, alpha=0.8)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Phase (°)")
    ax.set_title("FFT Phase")
    ax.axhline(0, color="grey", linewidth=0.5, linestyle="--")
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    ph_png = output_dir / "phase.png"
    fig.savefig(ph_png, dpi=150)
    plt.close(fig)
    console.print(f"  Phase plot   → [cyan]{ph_png}[/cyan]")


def _print_summary(params: SignalParameters, metrics: Any, output_dir: Path) -> None:  # type: ignore[type-arg]
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Value")

    table.add_row("Signal type", params.signal_type)
    table.add_row("Frequency", f"{params.frequency:.1f} Hz")
    table.add_row("Amplitude", str(params.amplitude))
    table.add_row("Duration", f"{params.duration:.3f} s")
    table.add_row("Sampling rate", f"{params.sampling_rate:.0f} Hz")
    table.add_row("FFT size", str(params.fft_size))
    table.add_row("", "")
    table.add_row("RMS", f"{metrics.rms:.6f}")
    table.add_row("Peak", f"{metrics.peak:.6f}")
    table.add_row("Crest factor", f"{metrics.crest_factor:.4f}")
    table.add_row(
        "SNR",
        f"{metrics.snr_db:.2f} dB" if metrics.snr_db is not None else "N/A (no noise)",
    )
    table.add_row("THD", f"{metrics.thd_db:.2f} dB")
    table.add_row("Peak frequency", f"{metrics.peak_freq:.4f} Hz")
    table.add_row("Output directory", str(output_dir.resolve()))

    console.print("\n")
    console.print(Panel(table, title="[bold]Analysis Summary[/bold]", border_style="green"))


# make Any available at module level for the type annotations above
from typing import Any  # noqa: E402
