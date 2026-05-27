.. _signal_analyzer_dev_guide:

***********************
Signal Analyzer — Design
***********************

The Signal Analyzer is the primary example application in this template.  It
demonstrates a production-representative pattern for a desktop scientific tool:
a typed parameter model with cross-field validation, a pure computation engine,
a Tkinter GUI that runs the engine off the main thread, and a headless CLI
command that reuses the same engine without the GUI.

.. contents:: On this page
   :local:
   :depth: 2


Package layout
==============

The signal analyzer spans three existing packages:

.. code-block:: text

    src/scaldys_template/
    ├── core/
    │   ├── signal_model.py       # SignalParameters — Pydantic model + validators
    │   ├── signal_engine.py      # generate_signal / compute_fft / compute_metrics
    │   └── parameter_store.py    # JSON save / load via AppLocation
    ├── tk/
    │   ├── app.py                # Application, MenuBar, SideBar, ToolBar
    │   └── ui/
    │       ├── editor_frame.py          # JSON Editor view
    │       └── analyzer/
    │           ├── analyzer_frame.py        # top-level GUI layout + async run wiring
    │           ├── signal_parameters_frame.py  # parameter entry widgets
    │           ├── plot_frame.py            # embedded matplotlib figures
    │           └── results_table_frame.py   # Treeview table + metrics bar
    └── cli/
        ├── commands/
        │   ├── cmd_gui.py          # ``gui`` command — launches the window
        │   └── cmd_analyze.py      # ``analyze`` command — headless CSV/PNG output

The three packages have a strict dependency order:

.. code-block:: text

    core/  ←  tk/ui/analyzer/  (GUI imports engine, never the other way)
    core/  ←  cli/commands/    (commands import engine, never the other way)
    tk/ui/ ←  cli/commands/cmd_gui  (cmd_gui imports Application)

This means the entire ``core/`` layer can be unit-tested without Tkinter,
matplotlib, or a display being present.


Core layer
==========

Signal model (``core/signal_model.py``)
----------------------------------------

``SignalParameters`` is a Pydantic ``BaseModel`` that acts as the single
validated data container for the whole pipeline.

Field-level validators (``@field_validator``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each numeric field has a range validator.  Pydantic runs these independently
so all field errors can be reported together:

.. code-block:: python

    @field_validator("frequency")
    @classmethod
    def check_frequency(cls, v: float) -> float:
        if not (0.1 <= v <= 10_000.0):
            raise ValueError("Frequency must be between 0.1 and 10 000 Hz.")
        return v

Cross-field validator (``@model_validator``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``check_cross_constraints`` runs **after** all field validators pass and
enforces three relationships:

1. **Nyquist criterion** — ``sampling_rate ≥ 2 × frequency``.  Violating this
   would cause aliasing: the generated spectrum would fold back on itself.

2. **Memory guard** — ``duration × sampling_rate ≤ MAX_SAMPLES`` (10 000 000).
   This prevents accidental multi-GB allocations.

3. **FFT size** — ``fft_size ≤ duration × sampling_rate``.  The FFT can only
   analyse samples that were generated.

.. code-block:: python

    @model_validator(mode="after")
    def check_cross_constraints(self) -> "SignalParameters":
        if self.sampling_rate < 2.0 * self.frequency:
            raise ValueError(...)
        total_samples = int(self.duration * self.sampling_rate)
        if total_samples > MAX_SAMPLES:
            raise ValueError(...)
        if self.fft_size > total_samples:
            raise ValueError(...)
        return self

Both the GUI and the CLI command create a ``SignalParameters`` instance before
calling any engine function.  All validation fires at construction time.

Enumerations
^^^^^^^^^^^^

``SignalType``, ``NoiseType``, and ``WindowType`` are ``StrEnum`` subclasses.
Using ``StrEnum`` means the values serialise to lowercase strings in JSON
(``"sine"``, ``"none"``, ``"hanning"``), making saved parameter files
human-readable.

Default values
^^^^^^^^^^^^^^

The defaults are chosen so that ``SignalParameters()`` (no arguments) is always
valid and produces a visually clear spectrum:

* **440 Hz** — A4 pitch; a single sharp spike in the FFT.
* **44 100 Hz** sampling rate — CD-quality standard; ``sampling_rate >> 2 × 440``.
* **0.1 s** duration — 4 410 samples; well above the default 1 024-point FFT.
* **1 024-point** Hanning FFT — good frequency resolution with low sidelobes.


Signal engine (``core/signal_engine.py``)
------------------------------------------

The engine is a set of pure functions — no I/O, no GUI, no state.  Each
function takes validated inputs and returns a typed dataclass.

.. code-block:: text

    generate_signal(params) → SignalData
    compute_fft(signal_data, params) → FFTResult
    compute_metrics(signal_data, fft_result) → SignalMetrics

Result containers
^^^^^^^^^^^^^^^^^

.. code-block:: python

    @dataclass
    class SignalData:
        time: np.ndarray        # shape (N,) — time axis in seconds
        signal: np.ndarray      # shape (N,) — clean waveform
        noise: np.ndarray       # shape (N,) — noise only (zeros if no noise)
        composite: np.ndarray   # shape (N,) — signal + noise + dc_offset
        sample_rate: float

    @dataclass
    class FFTResult:
        frequencies: np.ndarray   # shape (M,) — positive bins in Hz
        magnitude_db: np.ndarray  # shape (M,) — magnitude spectrum in dB
        phase_deg: np.ndarray     # shape (M,) — phase spectrum in degrees

    @dataclass
    class SignalMetrics:
        rms: float
        peak: float
        crest_factor: float       # peak / RMS
        snr_db: float | None      # None when no noise was added
        thd_db: float             # Total Harmonic Distortion (H2–H5)
        peak_freq: float          # dominant frequency bin in Hz

``generate_signal``
^^^^^^^^^^^^^^^^^^^

Uses ``np.linspace`` for the time axis (``endpoint=False``) so the last sample
never reaches ``duration``.  This is the standard convention for periodic
signals: a one-second, 1 000-sample array has samples at 0, 0.001, …, 0.999
(not 1.000), which avoids a duplicate when the signal is concatenated.

Noise power is derived from the requested SNR in dB:

.. code-block:: python

    signal_power = np.mean(raw**2)
    noise_power  = signal_power / (10.0 ** (snr_db / 10.0))
    noise_std    = np.sqrt(noise_power)

For Uniform noise, the standard deviation is matched to the Gaussian case
(``bound = noise_std × √3``) so the same SNR value produces the same
perceptual noise level regardless of noise type.

``compute_fft``
^^^^^^^^^^^^^^^

Only the first ``params.fft_size`` samples of ``composite`` are used.  This
ensures the transform length is always the validated power-of-two value.  The
window is applied before the transform:

.. code-block:: python

    segment = signal_data.composite[: params.fft_size]
    windowed = _apply_window(segment, params.fft_window)
    spectrum = np.fft.rfft(windowed)

Magnitude is normalised by ``fft_size / 2`` so that a full-scale sine reads
0 dB at its fundamental regardless of FFT size.  A floor of ``1e-12`` prevents
``log10(0)`` before the dB conversion.

``compute_metrics``
^^^^^^^^^^^^^^^^^^^

SNR is ``None`` (not zero) when no noise was added.  This distinction is
surfaced in the GUI metrics bar as *N/A* rather than a misleading 0 dB.

THD is computed from the linear magnitudes at harmonics 2–5 relative to the
fundamental bin.  It is a simplified estimate and should be treated as
indicative rather than precise.


Parameter persistence (``core/parameter_store.py``)
-----------------------------------------------------

``save_parameters`` / ``load_parameters`` are thin wrappers around Pydantic's
``model_dump_json()`` / ``model_validate()``.  They use ``AppLocation`` for the
default file path so that — like all other application data — parameters written
during a source-tree run land in ``<repo_root>/app_data/`` and not in the
user's installed-app data directory.

.. code-block:: python

    # Save
    path = default_parameters_path()   # app_data/signal_parameters.json
    save_parameters(params, path)

    # Load (raises pydantic.ValidationError if the file is invalid)
    params = load_parameters(path)

The ``load_parameters`` function applies full Pydantic validation to the loaded
data.  This means that a file edited by hand will fail loudly if a value is out
of range or a cross-field constraint is violated, rather than producing a silent
bad result.


GUI layer
=========

The GUI introduces no new patterns beyond what the template already
demonstrates.  Its three design goals are:

1. **Strict layer separation** — ``tk/ui/`` imports from ``core/``, never the
   reverse.  The engine has no knowledge of Tkinter, matplotlib, or widgets.

2. **Non-blocking execution** — the engine runs in a ``threading.Thread``
   so the Tkinter event loop is never blocked.

3. **Theme awareness** — matplotlib figures query the active ttkbootstrap theme
   at render time so they match the application's dark/light colour scheme.


``Application`` — state and file management
--------------------------------------------

``Application`` is the root ``tb.Window`` subclass that owns all shared state
and orchestrates the interaction between views.

Key attributes
^^^^^^^^^^^^^^

.. code-block:: python

    current_file: Path | None   # last opened/saved file (None until first save/open)
    _recent_files: list[Path]   # up to 10 most-recently used paths

Recent Files persistence
^^^^^^^^^^^^^^^^^^^^^^^^

``_load_recent_files()`` and ``_save_recent_files()`` use a plain JSON list
stored at ``AppLocation.AppDataDir / "recent_files.json"`` — the same directory
used by ``parameter_store.default_parameters_path()``, keeping all application
data co-located.  ``add_recent_file(path)`` prepends the new path, removes any
duplicate, and trims to 10 entries, then calls
``menubar.rebuild_recent_files_menu()`` to refresh the cascade.

File operations
^^^^^^^^^^^^^^^

All file I/O is handled by three ``Application`` methods:

* ``app_open_file()`` / ``app_open_recent_file(path)`` — load a JSON file,
  update ``current_file``, add to recent list, call ``update_parameters``.
* ``app_save_file()`` — save to ``current_file`` (falls back to Save As… if
  none is set).
* ``app_save_file_as()`` — show a save dialog, then call ``_do_save(path)``.

``_do_save(path)`` calls ``analyzer_frame.get_parameters()`` to obtain the
current validated model, then delegates to ``core.parameter_store.save_parameters``.

Parameter synchronisation
^^^^^^^^^^^^^^^^^^^^^^^^^^

``update_parameters(params, source)`` broadcasts a ``SignalParameters`` change
to all views while suppressing the originating view to avoid feedback loops:

.. code-block:: python

    def update_parameters(self, params: SignalParameters, source: str) -> None:
        if source != "analyzer":
            self.analyzer_frame.set_parameters(params)
        if source != "editor":
            self.editor_frame.set_json(params.model_dump_json(indent=2))

The ``source`` values used are ``"analyzer"`` (widget edit / reset),
``"editor"`` (Apply button result), and ``"file"`` (Open / Recent — updates
both views).  The :ref:`sync flow <sync_flow>` diagram below summarises the
data-flow for each trigger.

.. _sync_flow:

.. code-block:: text

    ┌───────────────────────────────────────────────────────────────┐
    │  Widget edit (FocusOut / ComboboxSelected)                     │
    │    SignalParametersFrame._notify_change()                      │
    │      → AnalyzerFrame._handle_params_changed(params)            │
    │          → Application.update_parameters(params, "analyzer")   │
    │              → editor_frame.set_json(...)          [editor only]│
    └───────────────────────────────────────────────────────────────┘
    ┌───────────────────────────────────────────────────────────────┐
    │  Apply button (EditorFrame)                                    │
    │    Application._apply_editor_json(json_text)                  │
    │      → analyzer_frame.set_parameters(params)  [analyzer only] │
    │      → editor_frame.set_json(canonical JSON)  [editor — norm] │
    └───────────────────────────────────────────────────────────────┘
    ┌───────────────────────────────────────────────────────────────┐
    │  File Open / Recent / Reset                                    │
    │    Application.update_parameters(params, "file")              │
    │      → analyzer_frame.set_parameters(params)  [both views]    │
    │      → editor_frame.set_json(...)                             │
    └───────────────────────────────────────────────────────────────┘

``_apply_editor_json`` re-populates the editor with the *canonical* (normalised)
JSON after a successful Apply — this confirms acceptance to the user and
standardises the format.


``SideBar`` and Navigation
--------------------------

The ``SideBar`` on the left edge of the window manages top-level navigation. It
is expanded by default to show labels but can be collapsed to icons-only.

Registered buttons
^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Button
     - Callback / view
   * - Signal Analyzer (``square-poll-vertical`` icon)
     - ``Application.show_analyzer_frame()``
   * - JSON Editor (``file-lines-regular`` icon)
     - ``Application.show_editor_frame()``
   * - UI Examples (``cubes`` icon)
     - ``Application.show_ui_examples_frame()``
   * - Navigation (``folder-tree`` icon)
     - ``Application.show_navigation_frame()``

**Selection synchronization**
    The sidebar maintains an "active" button state. When the user switches
    views (either by clicking a sidebar button or via application logic), the
    sidebar highlights the corresponding button with the theme's primary
    color. This provides a clear visual cue of the current application state.


``MenuBar`` — File menu
-----------------------

``MenuBar`` is constructed with an ``Application`` reference (``app: Application``)
so all commands route through ``Application`` rather than reaching into
``AnalyzerFrame`` directly:

.. code-block:: python

    class MenuBar(tb.Frame):
        def __init__(self, master, app: "Application", **kwargs):
            self._app = app
            ...

        def _cmd_open(self)    -> None: self._app.app_open_file()
        def _cmd_save(self)    -> None: self._app.app_save_file()
        def _cmd_save_as(self) -> None: self._app.app_save_file_as()

The Recent Files cascade menu is held as ``_recent_menu_nt`` (Windows custom
menubar) and ``_recent_menu_std`` (standard ``tk.Menu``).
``rebuild_recent_files_menu()`` repopulates both when the list changes:

.. code-block:: python

    def _populate_recent_menu(self, menu: tk.Menu) -> None:
        menu.delete(0, "end")
        for path in self._app._recent_files:
            menu.add_command(
                label=str(path),
                command=lambda p=path: self._app.app_open_recent_file(p),
            )


``ToolBar`` — Quick actions
---------------------------

The ``ToolBar`` provides a horizontal row of buttons for file operations and
analyzer controls. Like the ``MenuBar``, it routes all actions through the
``Application`` instance.

**Context-sensitive layout**
    The toolbar implements ``set_context(context)`` to show or hide buttons
    based on the active frame. This logic is triggered by the ``Application``
    view-switching methods (e.g., ``show_analyzer_frame()``).

    * ``"analyzer"``: Shows Open, Save, Run, and Defaults buttons.
    * ``"editor"``: Shows Open, Save, and Apply buttons.
    * ``"other"``: Hides the entire toolbar.

**Button wiring**
    * **Open / Save**: Wired to ``Application.app_open_file()`` and
      ``Application.app_save_file()``.
    * **Run / Defaults**: Wired to ``AnalyzerFrame._on_run()`` and
      ``AnalyzerFrame._on_reset()`` respectively.
    * **Apply**: Wired to ``EditorFrame._handle_apply()`` (which triggers the
      ``on_apply`` callback).


``EditorFrame`` — JSON parameter editing
-----------------------------------------

``EditorFrame`` is a thin view: it owns the text widget but contains no business
logic.  The **Apply** button, which previously lived in the header of this frame,
has been moved to the application toolbar for consistency with other frames.
All JSON parsing and state synchronisation live in
``Application._apply_editor_json()``.

Public API
^^^^^^^^^^

.. code-block:: python

    frame.set_json(text: str)     # replace content, clear error label
    frame.get_json() -> str       # return current content (trailing newline stripped)
    frame.show_error(msg: str)    # set / clear the status label

The ``on_apply`` constructor parameter accepts a ``Callable[[str], None]``.
``Application`` wires it to ``_apply_editor_json``:

.. code-block:: python

    self.editor_frame = EditorFrame(content, on_apply=self._apply_editor_json)

Apply validation
^^^^^^^^^^^^^^^^

``_apply_editor_json`` does two-phase validation:

1. ``json.loads(text)`` — ensures the text is valid JSON (catches syntax errors).
2. ``SignalParameters.model_validate(data)`` — applies all Pydantic field and
   cross-field validators.

On success both views are refreshed with the canonically serialised form of the
validated model, confirming acceptance to the user and normalising whitespace /
key ordering.  On failure the error message is shown in ``EditorFrame``'s status
label and no state changes.


``AnalyzerFrame`` — layout and run wiring
------------------------------------------

``AnalyzerFrame`` is a content widget registered with ``Application``.  It owns
the layout (left/right columns, vertical sash) and the run flow.

Change notification
^^^^^^^^^^^^^^^^^^^

``AnalyzerFrame`` accepts an optional ``on_params_changed`` callback.  It
forwards change notifications from ``SignalParametersFrame`` (user widget edits)
and from its own ``_on_reset()`` method so ``Application`` can stay in sync
without the frame importing ``Application`` directly:

.. code-block:: python

    self.analyzer_frame = AnalyzerFrame(
        content,
        on_params_changed=lambda p: self.update_parameters(p, "analyzer"),
    )

``get_parameters() -> SignalParameters | None`` and
``set_parameters(params)`` are the public API for reading and writing the
parameter panel from outside the frame.

The *Save parameters…* and *Load parameters…* buttons that previously lived in
the left panel have been removed; file operations are handled through the
File menu and the application toolbar.

Async run pattern
^^^^^^^^^^^^^^^^^

Tkinter is single-threaded: calling any long-running function from a widget
callback blocks the event loop and freezes the UI.  The signal engine is fast
(milliseconds), but the pattern shown here is the correct one for any
computation that might take longer.

The run flow uses three Python primitives:

.. code-block:: text

    1. threading.Thread  — runs the engine off the main thread
    2. queue.Queue       — carries the result (or error) back to the main thread
    3. self.after(100)   — polls the queue from the main thread at 100 ms intervals

.. code-block:: python

    def _on_run(self) -> None:
        params = self._params_frame.get_parameters()
        if params is None:
            return   # validation failed — error already shown

        self._run_btn.configure(state="disabled")
        self._progress.start(10)

        def _worker() -> None:
            try:
                sd  = generate_signal(params)
                fft = compute_fft(sd, params)
                mtr = compute_metrics(sd, fft)
                self._result_queue.put(("ok", sd, fft, mtr, params))
            except Exception as exc:
                self._result_queue.put(("error", str(exc)))

        threading.Thread(target=_worker, daemon=True, name="signal-engine").start()
        self.after(100, self._poll_result)

    def _poll_result(self) -> None:
        try:
            item = self._result_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_result)   # reschedule and return
            return

        self._progress.stop()
        self._run_btn.configure(state="normal")

        if item[0] == "ok":
            _, sd, fft, mtr, params = item
            self._table_frame.update_results(sd, fft, mtr)
            self._plot_frame.update_plots(sd, fft, params)
        else:
            messagebox.showerror("Analysis Error", item[1])

**Why ``queue.Queue`` and not a shared variable?**

A plain attribute written from the worker thread and read from the main thread
would be a data race — Python's GIL makes it unlikely to corrupt memory, but
the visibility of the write is not guaranteed without synchronisation.
``queue.Queue`` provides the necessary memory barrier.

**Why ``daemon=True``?**

A daemon thread does not prevent the Python interpreter from exiting.  If the
user closes the window while a computation is running, the thread is killed
automatically.  For a millisecond computation this is acceptable; for a
long-running job, you would also wire ``_shutdown_event`` into the worker to
allow graceful cancellation.


``SignalParametersFrame`` — widget-to-model bridge
---------------------------------------------------

The frame's public API is intentionally minimal:

.. code-block:: python

    params: SignalParameters | None = frame.get_parameters()
    frame.set_parameters(params)

``get_parameters()`` reads every widget, assembles a raw ``dict``, and
constructs a ``SignalParameters``.  If construction raises ``ValidationError``,
the first error message is shown in the status label below the grid and the
offending widget is highlighted in red.  The method returns ``None`` on
failure.

``set_parameters(params)`` is the reverse: it writes every widget without
triggering validation callbacks, then calls ``_on_noise_type_changed()`` to
restore the correct enable/disable state of the SNR field.
**Calling ``set_parameters`` does not fire ``on_change``**; only genuine user
interactions do.

Change notification callback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An optional ``on_change: Callable[[SignalParameters | None], None]`` constructor
parameter allows callers to react to user edits without polling.  The callback
fires on:

* ``<FocusOut>`` for all numeric ``tb.Spinbox`` / ``tb.Entry`` widgets.
* ``<<ComboboxSelected>>`` for all ``tb.Combobox`` widgets.

These are the right events to use for sync because they fire *after* the user
has committed a change, not on every keystroke.  Using raw ``StringVar`` traces
would fire on every key press and trigger redundant JSON serialisations during
numeric entry.

The callback receives the result of ``_parse_parameters()``:

.. code-block:: python

    def _parse_parameters(self) -> SignalParameters | None:
        """Parse current widget state silently without updating the UI."""
        try:
            return SignalParameters(
                signal_type=...,
                frequency=float(self._vars["frequency"].get()),
                ...
            )
        except (ValueError, IndexError, ValidationError):
            return None

Using a silent helper keeps the change-notification path free of side effects:
the existing per-field validation and status-label update logic in
``get_parameters()`` is not disturbed.

Noise-type gating
^^^^^^^^^^^^^^^^^

The SNR field is meaningless when *Noise type* is *None*.  A
``trace_add("write", ...)`` on the ``noise_type`` ``StringVar`` calls
``_on_noise_type_changed()`` whenever the combobox selection changes:

.. code-block:: python

    def _on_noise_type_changed(self, *_: Any) -> None:
        label = self._vars["noise_type"].get()
        noise = _NOISE_TYPE_VALUES[_NOISE_TYPE_LABELS.index(label)]
        state = "normal" if noise != NoiseType.NONE else "disabled"
        self._widgets["snr_db"].configure(state=state)

Note on ``tb.LabelFrame`` and padding
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ttkbootstrap.LabelFrame`` is backed by the classic ``tk.LabelFrame`` (not
``ttk::labelframe``).  Classic ``tk.LabelFrame`` does not support the
``-padding`` option.  Inner padding is therefore applied to the first child
``tb.Frame``, which *is* a ``ttk.Frame`` and does support ``padding``:

.. code-block:: python

    outer = tb.Frame(self, padding=8)   # padding applied here, not to LabelFrame
    outer.pack(fill=BOTH, expand=YES)


``PlotFrame`` — embedded matplotlib
-------------------------------------

Each of the three plot tabs is a ``_PlotTab`` instance containing:

* A ``matplotlib.figure.Figure`` + ``Axes``.
* A ``FigureCanvasTkAgg`` that embeds the figure into the Tkinter frame.
* A ``NavigationToolbar2Tk`` that provides zoom, pan, and save-as-PNG for free.

Theme awareness
^^^^^^^^^^^^^^^

``_theme_colors()`` queries ``tb.Style()`` (the ttkbootstrap singleton) at
render time to determine whether the active theme is dark or light:

.. code-block:: python

    def _theme_colors() -> tuple[str, str, str, str]:
        style = tb.Style()
        if style.theme.type == "dark":
            return "#1e1e2e", "#2a2a3e", "#e0e0e0", "#444466"
        else:
            return "#f8f8f8", "#ffffff", "#222222", "#cccccc"

``_apply_theme(fig, axes)`` then sets figure background, axes background,
tick colours, axis label colours, spine colours, and grid colours.  This is
called at the end of every ``_draw_*`` method so the colour scheme stays in
sync if the user switches themes during a session.

Performance
^^^^^^^^^^^

Long signals are downsampled to ``_MAX_PLOT_POINTS`` (4 000) before plotting:

.. code-block:: python

    step = max(1, n // _MAX_PLOT_POINTS)
    t = signal_data.time[::step]

This keeps the plot responsive for long-duration signals (e.g. 60 s at 44 100 Hz
= 2 646 000 samples) without affecting the FFT results, which always use the
full ``fft_size`` samples.

matplotlib backend
^^^^^^^^^^^^^^^^^^

The TkAgg backend is set at module level, before any ``pyplot`` import:

.. code-block:: python

    import matplotlib
    matplotlib.use("TkAgg")   # must be before pyplot

The ``analyze`` CLI command (headless) uses the *Agg* backend instead:

.. code-block:: python

    matplotlib.use("Agg")     # no display required

Both calls are local (inside the command/module) rather than global so they do
not affect other code that might import matplotlib independently.


``ResultsTableFrame`` — Treeview and export
--------------------------------------------

The ``ttk.Treeview`` widget does not virtualise rows — all items are in memory.
For a signal with 4 410 samples (default) this is fine, but a 10-second signal
at 44 100 Hz would produce 441 000 rows, which would freeze the UI during
insertion.  The table therefore downsamples the time-domain data to
``_MAX_DISPLAY_ROWS`` (2 000) for the visual table, while the CSV export in
``_export_csv()`` always writes every sample:

.. code-block:: python

    step = max(1, n // _MAX_DISPLAY_ROWS)
    for i in range(0, n, step):
        tree.insert("", END, values=(...))


CLI layer
=========

``cmd_gui.py`` — ``gui`` command
---------------------------------

``cmd_gui.py`` imports ``Application`` (and by extension Tkinter and matplotlib)
**inside** the command function, not at module level:

.. code-block:: python

    def gui(...) -> None:
        from scaldys_template.tk.app import Application
        app = Application()
        ...
        app.mainloop()

This deferred import ensures that the Tkinter/matplotlib stack is only loaded
when the ``gui`` command is actually invoked.  Running ``scaldys-template analyze``
or ``scaldys-template process`` does not pay the Tkinter import cost.

The optional ``--params`` argument uses ``self.after(200, _load_on_startup)``
to defer the parameter load until after the window's first render cycle.  This
avoids a race condition where ``_params_frame`` is not yet fully constructed
when the load fires.


``cmd_analyze.py`` — ``analyze`` command
-----------------------------------------

The ``analyze`` command is intentionally a thin orchestration layer:

1. Resolve parameters (from file or defaults).
2. Resolve output directory.
3. Call ``generate_signal`` → ``compute_fft`` → ``compute_metrics``.
4. Write CSV files.
5. Write PNG plots (unless ``--no-plots``).
6. Print a summary panel.

The same engine functions used by the GUI are called here without modification.
This is the key benefit of the layer separation: the engine is tested once
(in ``tests/unit/core/``) and both the GUI and CLI paths are covered by those
same tests.

Plot generation uses ``matplotlib.use("Agg")`` (no display required) inside
``_save_plots()``.  This is safe to call inside the function because matplotlib
has not yet been imported elsewhere in the CLI path (the GUI import is deferred
as described above).

The ``--no-plots`` flag skips ``_save_plots()`` entirely.  This is important
for CI environments where no display is available: even the Agg backend
occasionally triggers X11 imports on Linux depending on the matplotlib build.


Testing
=======

Coverage breakdown
------------------

.. list-table::
   :widths: 45 55
   :header-rows: 1

   * - Test file
     - What it covers
   * - ``tests/unit/core/test_signal_model.py``
     - Field validators (boundary values), cross-field Nyquist / FFT-size /
       memory-guard rules, JSON round-trip serialisation.
   * - ``tests/unit/core/test_signal_engine.py``
     - Known-correct outputs: RMS of a sine, peak amplitude, crest factor,
       FFT bin alignment, phase range, SNR measurement.
   * - ``tests/unit/core/test_parameter_store.py``
     - Save/load round-trip, parent-directory creation, error handling for
       missing or invalid files.
   * - ``tests/integration/test_cli_analyze.py``
     - End-to-end CLI invocations via ``typer.testing.CliRunner``: CSV file
       creation, column headers, metrics values, force/no-force behaviour,
       invalid parameter file handling.
   * - ``tests/unit/tk/test_app_state.py``
     - GUI state and navigation: sidebar expansion, button selection
       highlighting, and view switching logic.

GUI testing is performed using standard unit tests that instantiate the
``Application``.  These tests verify widget states and styles but require a
valid Tcl/Tk environment; they are automatically skipped in headless CI
environments.  The layer separation ensures that even without GUI tests, the
business-critical code (model, engine, persistence) is fully covered by
platform-independent unit tests.

Key testing patterns
--------------------

**Known-correct signal values**

Analytical results for a sine wave are used as ground truth:

.. code-block:: python

    # RMS of a sine with amplitude A is A / sqrt(2)
    assert metrics.rms == pytest.approx(amplitude / 2.0**0.5, rel=0.01)

    # Crest factor of a pure sine is sqrt(2)
    assert metrics.crest_factor == pytest.approx(2.0**0.5, rel=0.02)

**FFT bin alignment**

The peak FFT bin should fall within one bin width of the configured frequency:

.. code-block:: python

    bin_width = params.sampling_rate / params.fft_size
    assert abs(metrics.peak_freq - freq) <= bin_width

**Stochastic tolerance**

Tests involving generated noise allow ±3 dB tolerance because the noise
arrays are random:

.. code-block:: python

    # SNR should be within 3 dB of the requested value
    assert abs(measured_snr - 20.0) < 3.0

**CLI via CliRunner**

Integration tests use Typer's ``CliRunner`` rather than ``subprocess``.
This avoids spawning a new process for every test and keeps the test suite
fast:

.. code-block:: python

    runner = CliRunner()
    result = runner.invoke(app, ["analyze", "--output", str(out), "--no-plots"])
    assert result.exit_code == 0, result.output
