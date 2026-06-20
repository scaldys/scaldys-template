# Release Notes

This document contains high-level highlights of each release, focused on new
features and improvements for end users. For a technical list of all changes,
please see the [CHANGELOG](./CHANGELOG).

---

## [0.11.0] - 2026-06-20

This release introduces a major focus on the **graphical user interface** based
on TkInter, transitioning from a pure CLI tool to a hybrid application. Note
that while the CLI remains cross-platform, the GUI components are currently only
tested on **Windows**.

- **Signal Analyzer GUI**: Full feature implementation including core model,
  engine, and persistence logic. GUI components (frames, plots, table) moved
  into a dedicated `gui/signal_analyzer/` directory.
- **JSON Editor view**: A new sidebar frame that displays the current
  `SignalParameters` as formatted JSON in an editable text widget. Bidirectional
  sync keeps both views consistent: widget edits in the Analyzer update the
  editor in real time, and "Apply" (from the toolbar) updates the Analyzer
  widgets.
- **Enhanced File menu**: The File menu now contains _Open…_, _Save_, _Save
  As…_, and a _Recent Files_ cascade (up to 10 entries). All file operations are
  centralised in the main application.
- **ToolBar component**: Provides quick access to File operations (Open, Save)
  and Analyzer controls (Run, Defaults). The toolbar automatically adjusts its
  visibility and content based on the active frame.
- **About dialog**: New dialog exposing application metadata (version, author,
  licence). The `Help` menu has been updated to surface the dialog.
- **Python 3.13 Support**: Full support for the latest Python release in all CI
  workflows and environments.
- **UI Examples Showcase**: A dedicated frame demonstrating the various
  ttkbootstrap` widgets and styles used in the application.
- **Visual Improvements**: Updated FontAwesome icons (v7.2.0) and adjusted
  widget styles for better visual consistency across the application.

---

## [0.10.0] - 2026-05-20

This is the first public release of the Scaldys Template, establishing a robust
foundation for modern Python development with a focus on CLI applications and
Windows deployment.

- **CLI Foundation**: A production-ready CLI structure built with `Typer`,
  featuring global logging configuration and persisted settings management.
- **Core Scaffolds**: Reference implementations for asynchronous processing
  pipelines and database abstraction layers.
- **Application Lifecycle**: A managed entry point (`__main__.py`) that handles
  crash hooks, signal interrupts, and environment validation.
- **Windows Build System**: Integrated support for creating portable executables
  (PyInstaller) and professional installers (Inno Setup).
- **Quality Gates**: Pre-configured workflows for `pytest`, `ruff`
  (linting/formatting), and `pyright` (type checking) to ensure high code
  quality from the start.

---
