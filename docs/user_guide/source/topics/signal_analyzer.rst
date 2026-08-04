.. _signal_analyzer_user_guide:

***************
Signal Analyzer
***************

The Signal Analyzer generates synthetic waveforms, computes their frequency
spectrum using the Fast Fourier Transform (FFT), and displays the results in
interactive plots and a scrollable data table.  It is available both as a
graphical application and as a headless CLI command for scripting or CI use.

.. contents:: On this page
   :local:
   :depth: 2


Launching the application
=========================

Graphical interface
-------------------

.. code-block:: console

    scaldys-template gui

The main window opens immediately and is pre-populated with default parameters
(440 Hz sine wave, 44 100 Hz sampling rate, 0.1 s duration).  You can start
exploring right away — press **F5** or click **▶ Run** to see the first result.

To open the GUI with a previously saved parameter file loaded automatically:

.. code-block:: console

    scaldys-template gui --params my_params.json

Troubleshooting startup
-----------------------

If the application fails to start or closes immediately, you can use the global
``--verbose`` flag to see detailed logs in the terminal. Note that global flags
must appear *before* the ``gui`` command:

.. code-block:: console

    scaldys-template --verbose gui

When running with ``--verbose``, the application preserves its standard output
and error streams (which are normally suppressed for the detached GUI process),
allowing you to see critical error messages and tracebacks.


Headless CLI (no window)
------------------------

.. code-block:: console

    scaldys-template analyze                           # use built-in defaults
    scaldys-template analyze params.json               # load parameters from file
    scaldys-template analyze params.json --output ./results
    scaldys-template analyze params.json --output ./results --force

The ``analyze`` command writes CSV files and PNG plots to a directory (see
:ref:`headless_analyze_command`) and exits, without opening any window.


The GUI application
===================

Layout overview
---------------

The window is structured with a navigation sidebar on the far left, a toolbar
at the top, and the main content area occupying the rest of the space.

* **Sidebar** — provides navigation between application frames.  It is expanded
  by default to show labels but can be collapsed to icons-only using the
  hamburger button at the top.  The active frame's button is highlighted with
  the theme's primary color.  Available frames:

  * **Signal Analyzer** — graphical parameter entry and results view.
  * **JSON Editor** — text-based JSON view of the same parameters (see below).
  * **UI Examples** — widget showcase.
  * **Navigation** — tree navigator example.

* **Toolbar** — provides quick access to file operations and analyzer controls.
  The toolbar is context-sensitive: it shows relevant buttons based on the
  active frame (see `Toolbar` below).

* **Main area** — shows the currently selected frame.  For the Signal Analyzer,
  this is further divided into:

  * **Parameter panel** (left) — signal, noise, and FFT configuration.
  * **Plot tabs** (top right) — Time Domain, Spectrum, and Phase plots.
  * **Results table** (bottom right) — numerical data and metrics bar.

A resizable splitter separates the plots from the table in the main area; drag
it vertically to give more space to whichever panel you need.


Toolbar
-------

The toolbar is located below the menu bar and provides buttons for common
actions.

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Button
     - Description
   * - **Open**
     - Open a JSON parameter file. Same as *File → Open…*.
   * - **Save**
     - Save current parameters. Same as *File → Save*.
   * - **Run**
     - Execute the signal analysis. Same as **F5** or the **Run** button in
       the parameter panel.
   * - **Defaults**
     - Restore factory default parameters. Same as **Reset to defaults** in
       the parameter panel.
   * - **Apply**
     - Parse and validate the JSON text in the editor and synchronize it with
       the Analyzer. Only visible in the **JSON Editor**.

Contextual availability
^^^^^^^^^^^^^^^^^^^^^^^

To reduce clutter, the toolbar automatically adjusts its content based on the
active frame:

* **Signal Analyzer**: All buttons (Open, Save, Run, Defaults) are visible.
* **JSON Editor**: The **Open**, **Save**, and **Apply** buttons are visible.
  Analyzer controls (Run, Defaults) are hidden.
* **UI Examples / Navigation**: The entire toolbar is hidden as these frames
  do not support file or analyzer operations.


Parameter panel
---------------

The parameter panel is grouped into three sections.

**Signal shape**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Parameter
     - Description
   * - Signal type
     - Waveform shape: *Sine*, *Square*, *Sawtooth*, *Triangle*, or
       *White Noise*.
   * - Frequency (Hz)
     - Fundamental frequency of the waveform.  Range: 0.1 – 10 000 Hz.
   * - Amplitude
     - Peak amplitude of the clean waveform (before noise or DC offset).
       Must be > 0.
   * - Duration (s)
     - Length of the generated signal.  Range: 0.001 – 60 s.
   * - Sampling rate (Hz)
     - Number of samples per second.  Must be **at least twice the
       frequency** (Nyquist criterion).
   * - Phase offset (°)
     - Starting phase of the waveform.  Range: 0 – 360°.
   * - DC offset
     - Constant value added to every sample.  Shifts the waveform up or
       down.  Use 0 for no offset.

**Noise**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Parameter
     - Description
   * - Noise type
     - *None* (no noise), *Gaussian* (normally distributed), or *Uniform*
       (uniformly distributed).
   * - Noise SNR (dB)
     - Signal-to-noise ratio in decibels.  Only active when noise type is
       not *None*.  Lower values mean more noise.  Typical range: 0 – 40 dB.

**FFT**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Parameter
     - Description
   * - FFT window
     - Window function applied before the transform: *Rectangular*,
       *Hanning*, *Hamming*, or *Blackman*.  Hanning is a good default.
   * - FFT size
     - Number of samples used for the FFT.  Must be a power of two and
       no larger than the total number of generated samples
       (duration × sampling rate).

Validation
^^^^^^^^^^

Parameters are validated before any computation begins:

* Fields that contain an invalid value are highlighted in red.
* A message below the parameter panel explains the problem (for example,
  *"Sampling rate must be ≥ 2× frequency"*).
* The **▶ Run** button is not disabled — clicking it while errors are present
  will show the first validation error without running the engine.


Running an analysis
-------------------

Click **▶ Run** (in the parameter panel or the toolbar) or press **F5**.

While the engine is running (typically a few milliseconds), the progress bar
below the button animates.  The button is disabled for the duration of the run.

When complete:

* The three plot tabs update.
* The results table is populated.
* The metrics bar shows scalar summary values.

If an error occurs (for example, a parameter that slipped past field-level
validation), a dialog displays the error message.


Plots
-----

The right-hand panel has three tabs.

Time Domain
^^^^^^^^^^^

Shows the generated signal plotted against time.

* The **composite** waveform (signal + noise + DC offset) is drawn in blue.
* When noise is enabled, the **clean signal** is overlaid in green (dashed)
  and the **noise** component in amber (dotted).

Use the Navigation Toolbar at the bottom of the plot to zoom in on a region,
pan, or save the plot as a PNG file.

Spectrum
^^^^^^^^

Shows the FFT magnitude in decibels plotted against frequency.

* Peaks correspond to frequency components in the signal.
* The window function affects spectral leakage: *Rectangular* has the sharpest
  main lobe but high sidelobes; *Blackman* has the widest main lobe but very
  low sidelobes.

Phase
^^^^^

Shows the FFT phase in degrees plotted against frequency.  The phase is only
meaningful at frequencies where the signal has significant power.


Metrics bar
-----------

The metrics bar above the results table shows six scalar values computed from
the current run:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Metric
     - Description
   * - RMS
     - Root-mean-square amplitude of the composite waveform.  For a pure
       sine wave with amplitude *A*, RMS ≈ *A* / √2.
   * - Peak
     - Maximum absolute amplitude of the composite waveform.
   * - Crest factor
     - Peak / RMS.  A pure sine has a crest factor of √2 ≈ 1.414.  Square
       waves have a crest factor of 1; impulsive signals have high values.
   * - SNR (dB)
     - Measured signal-to-noise ratio, computed from the generated arrays.
       Shows *N/A* when no noise was requested.
   * - THD (dB)
     - Total Harmonic Distortion — ratio of harmonic power (harmonics 2–5)
       to fundamental power.  Only meaningful for periodic waveforms.
   * - Peak freq (Hz)
     - Frequency of the highest-magnitude FFT bin.  Should match the
       configured frequency for clean periodic signals.


Results table
-------------

The table panel has two tabs.

**Time Domain tab**

Each row is one time sample with four columns:

* *Time (s)* — sample timestamp.
* *Signal* — clean waveform value.
* *Noise* — noise component (zero if no noise was configured).
* *Composite* — signal + noise + DC offset.

For performance, very long signals are downsampled to 2 000 rows in the table
display.  The CSV export always contains the full signal.

**Frequency Domain tab**

Each row is one FFT bin:

* *Frequency (Hz)* — centre frequency of the bin.
* *Magnitude (dB)* — spectral magnitude.
* *Phase (°)* — spectral phase.


File management
===============

The **File** menu (menu bar at the top) provides all parameter file operations.

Open…
-----

*File → Open…* (or **Ctrl+O**, or the **Open** toolbar button) opens a
file-picker dialog.  Select any previously saved ``.json`` parameter file.
Both the Analyzer widgets and the JSON Editor update immediately.  The
analysis does not run automatically — press **▶ Run** when ready.

Save / Save As…
---------------

*File → Save* (or **Ctrl+S**, or the **Save** toolbar button) writes the
current parameters to the last-opened file.  If no file has been opened yet,
it behaves like *Save As…*.

*File → Save As…* opens a save dialog and writes a new ``.json`` file.

Example saved file:

.. code-block:: json

    {
      "signal_type": "sine",
      "frequency": 440.0,
      "amplitude": 1.0,
      "duration": 0.1,
      "sampling_rate": 44100.0,
      "fft_window": "hanning",
      "fft_size": 1024
    }

Recent Files
------------

*File → Recent Files* shows the last 10 opened or saved files.  Click any
entry to reload it immediately.  The list persists across application restarts.

Reset to defaults
-----------------

Click **Defaults** in the toolbar or **Reset to defaults** (in the Analyzer's
left panel) to restore the factory default parameter values (440 Hz sine,
44 100 Hz, 0.1 s, Hanning window, 1 024-point FFT).  Both the Analyzer widgets
and the JSON Editor reset.


JSON Editor
===========

The **JSON Editor** view (sidebar → file-lines icon) shows the current
``SignalParameters`` as formatted JSON text in an editable text area.

Bidirectional sync
------------------

* **Analyzer → Editor**: whenever you finish editing a widget in the Analyzer
  (on focus-out for numeric fields, or on selection for dropdowns) the JSON
  Editor updates automatically.
* **Editor → Analyzer**: edit the JSON text directly, then click **Apply**
  in the toolbar.  The text is parsed and validated; if successful, the Analyzer
  widgets update.  If the JSON is invalid or a value fails validation, an error
  message is shown below the text area and no state is changed.

Typical use cases
-----------------

* **Copy/paste a configuration** — paste a JSON snippet from a colleague or a
  script directly into the editor and click Apply.
* **Bulk edit** — change multiple fields at once in the text rather than
  clicking through each widget.
* **Inspect the serialised form** — see exactly what will be written to disk
  before saving.


Exporting results
=================

From the GUI
------------

Click the **Export CSV…** button in the results table panel to save both the
time-domain and frequency-domain data to a single CSV file.  The file contains
two sections separated by a blank line, each with a ``#`` comment header.

Plots can be saved individually using the **Save** button |save-icon| in the
Navigation Toolbar below each plot tab.

From the CLI
------------

Use the ``analyze`` command with a parameter file:

.. code-block:: console

    scaldys-template analyze params.json --output ./my_results

This writes three CSV files and three PNG plots to ``./my_results/``:

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - File
     - Contents
   * - ``time_domain.csv``
     - Full time-domain signal (all samples).
   * - ``frequency_domain.csv``
     - Full FFT result (all frequency bins).
   * - ``metrics.csv``
     - Scalar metrics (RMS, peak, crest factor, SNR, THD, peak frequency).
   * - ``time_domain.png``
     - Time-domain waveform plot.
   * - ``spectrum.png``
     - FFT magnitude spectrum plot.
   * - ``phase.png``
     - FFT phase spectrum plot.


.. _headless_analyze_command:

Headless ``analyze`` command
=============================

The ``analyze`` command runs the full analysis pipeline without opening a
window.  All output goes to a directory.

.. code-block:: console

    scaldys-template analyze [PARAMS_FILE] [OPTIONS]

**Arguments**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Argument
     - Description
   * - ``PARAMS_FILE``
     - Optional path to a JSON parameter file.  When omitted, built-in
       default parameters are used.

**Options**

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Option
     - Description
   * - ``--output / -o``
     - Output directory.  Defaults to ``<app_data>/analyze_output``.
   * - ``--force / -f``
     - Overwrite the output directory if it already exists.  Without this
       flag the command exits with an error if the directory exists.
   * - ``--no-plots``
     - Skip PNG plot generation.  Useful in headless or CI environments
       where a display is not available.

**Examples**

.. code-block:: console

    # Use defaults, write to <app_data>/analyze_output
    scaldys-template analyze

    # Load parameters, save to ./results, overwrite if present
    scaldys-template analyze sine_440hz.json --output ./results --force

    # CI mode: CSV only, no display required
    scaldys-template analyze params.json --output ./ci_results --no-plots


Keyboard shortcuts
==================

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Shortcut
     - Action
   * - **F5**
     - Run analysis
   * - **Ctrl+S**
     - Save parameters (Save As… if no current file)
   * - **Ctrl+O**
     - Open parameters file
   * - **Ctrl+Q**
     - Close the application


.. |save-icon| unicode:: U+1F4BE
