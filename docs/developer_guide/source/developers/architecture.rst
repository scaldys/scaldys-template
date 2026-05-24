.. _architecture:

************
Architecture
************

``scaldys-template`` is structured around **four top-level packages** inside
``src/scaldys_template/``, each with a single responsibility:

* **cli/** — argument parsing, global options, command routing, settings.
* **common/** — shared infrastructure (paths, logging) with no dependency on
  the CLI or on domain logic.
* **core/** — domain logic: reference stubs (export, async processing, database)
  plus the Signal Analyzer engine.
* **tk/** — the Tkinter GUI application (Signal Analyzer window).

The module layout mirrors this split:

.. code-block:: text

    src/scaldys_template/
    ├── __about__.py            # APP_NAME, PACKAGE_NAME, VERSION constants
    ├── __init__.py             # re-exports cli.* and common.*
    ├── __main__.py             # lifecycle entry point (freeze_support → app())
    ├── py.typed                # PEP 561 marker — package ships type stubs
    ├── cli/
    │   ├── cli.py              # Typer app, HeaderGroup, app callback
    │   ├── settings.py         # AppSettings — INI persistence + Pydantic validation
    │   └── commands/
    │       ├── arg_types.py    # Shared Annotated type aliases (ARG_TYPE_VERBOSE, …)
    │       ├── cmd_analyze.py  # analyze command — headless CSV/PNG output
    │       ├── cmd_export.py   # export command
    │       ├── cmd_gui.py      # gui command — launches the Tkinter window
    │       ├── cmd_process.py  # process command (async demo)
    │       └── cmd_settings.py # settings sub-app
    ├── common/
    │   ├── app_location.py     # AppLocation — cross-platform directory resolution
    │   └── logging.py          # setup_logging(), JsonFormatter, NonErrorFilter
    ├── core/
    │   ├── async_processor.py  # process_items() — async pipeline template
    │   ├── database.py         # DatabaseConnection, ConnectionPool, transaction()
    │   ├── export.py           # export_data() — data serialisation stub
    │   ├── signal_engine.py    # generate_signal / compute_fft / compute_metrics
    │   ├── signal_model.py     # SignalParameters — Pydantic model + validators
    │   └── parameter_store.py  # JSON save/load via AppLocation
    └── tk/
        ├── app.py              # Application window, MenuBar, ToolBar, SideBar
        ├── fontawesome_icons.py
        ├── styles.py
        ├── utils.py
        └── ui/
            ├── analyzer_frame.py        # top-level Signal Analyzer layout
            ├── example_frame.py         # ttkbootstrap widget showcase
            ├── play_frame.py            # play/demo panel
            ├── plot_frame.py            # embedded matplotlib figures
            ├── results_table_frame.py   # Treeview + metrics bar + CSV export
            └── signal_parameters_frame.py  # parameter entry widgets

.. contents:: On this page
   :local:
   :depth: 2


Lifecycle entry point (``__main__.py``)
=======================================

``__main__.py`` is the single entry point for all execution paths — installed
CLI, ``python -m scaldys_template``, and frozen PyInstaller binary.  Its *only*
responsibility is the startup sequence; it contains no domain logic.

The numbered sequence in ``main()`` is intentional and must not be reordered:

.. code-block:: python

    def main() -> None:
        multiprocessing.freeze_support()   # (1) must be first for frozen multiprocessing
        _pre_init_logging()                # (2) CRITICAL-only stderr fallback
        _setup_crash_hook()                # (3) clean exit on unhandled exceptions
        _setup_signal_handlers()           # (4) graceful shutdown on SIGINT/SIGTERM
        _setup_asyncio_policy()            # (5) correct event loop for Windows async I/O
        _validate_environment()            # (6) fail fast on bad environment
        app()                              # (7) Typer CLI — calls setup_logging via callback

**Why the ordering matters:**

1. ``freeze_support()`` must be the absolute first call — if the frozen
   executable spawns child processes (multiprocessing), the child re-runs
   ``main()`` and ``freeze_support()`` intercepts it before any side effects.

2. Pre-init logging installs a CRITICAL-only ``basicConfig`` fallback so any
   exception raised in steps 3–6 is visible on stderr instead of being silently
   swallowed.

3. The crash hook replaces ``sys.excepthook``.  If this is installed after
   threads are started, a crash on another thread could bypass it.

4. Signal handlers must be registered from the main thread before any other
   threads are created.

5. The asyncio event loop policy must be set before the first event loop is
   created — that happens inside ``asyncio.run()`` in ``async_processor.py``.

6. Environment validation is a fast-fail guard; it runs before Typer/Click
   start parsing, so the error message is clean rather than a Typer usage
   error.


Shutdown event
--------------

``__main__.py`` exports a module-level ``threading.Event``:

.. code-block:: python

    from scaldys_template.__main__ import _shutdown_event

Any long-running loop — the async pipeline, a polling loop, a server — should
check ``_shutdown_event.is_set()`` between iterations to participate in
cooperative shutdown.  When SIGINT or SIGTERM arrives, the signal handler sets
the event and raises ``KeyboardInterrupt``; the event gives async/threaded code
a chance to drain cleanly before the process exits.


CLI layer (``cli/``)
====================

Typer app setup
---------------

The Typer app is created in ``cli.py`` with a custom ``HeaderGroup`` that
prints ASCII art above the help text:

.. code-block:: python

    app = typer.Typer(
        cls=HeaderGroup,
        callback=main,
        no_args_is_help=True,
        add_completion=False,
        rich_markup_mode="rich",
    )

    app.command()(cmd_export.export)
    app.command()(cmd_process.process)
    app.add_typer(cmd_settings.app, name="settings")

Commands are registered by passing the command function directly to
``app.command()``.  Sub-apps (like ``settings``) are registered with
``app.add_typer()``.

App callback and logging ownership
-----------------------------------

The ``main()`` callback (invoked before every subcommand) is the **single,
authoritative place where logging is configured**.  Individual commands must
not call ``setup_logging()``; doing so after the callback runs would
reconfigure the already-running ``QueueListener``.

The callback resolves the effective log level by checking the CLI flag first
and falling back to the persisted ``AppSettings.log_level``:

.. code-block:: python

    if log_level is None:
        log_level = AppSettings().log_level
    setup_logging(log_level, verbose)

Global options (``--log``, ``--verbose``) must appear *before* the subcommand
name on the command line because Typer processes them as part of the top-level
app callback, not as command options.

Shared argument types
---------------------

``commands/arg_types.py`` defines reusable ``Annotated`` type aliases:

.. code-block:: python

    ARG_TYPE_VERBOSE = Annotated[bool, typer.Option("--verbose", "-v", ...)]
    ARG_TYPE_LOG_LEVEL = Annotated[Optional[str], typer.Option("--log", "-l", ...)]

Using ``Annotated`` aliases keeps command signatures concise and ensures the
same help text and flag names are used everywhere.  Command-specific arguments
are defined locally inside each command module.

Default argument evaluation
----------------------------

Typer evaluates default argument expressions at import time.  Defaults that
call ``AppLocation.get_directory()`` (which calls ``logger.debug()``) must be
resolved inside the command body instead:

.. code-block:: python

    # WRONG — evaluated at import time, before logging is configured:
    def export(output_dir: Path = AppLocation.get_directory(...)):

    # RIGHT — resolved at call time:
    def export(output_dir: Path | None = None):
        if output_dir is None:
            output_dir = AppLocation.get_directory(AppLocation.AppDataDir)


Settings (``cli/settings.py``)
================================

``AppSettings`` wraps a Pydantic model around an INI file.  The two-layer
design separates concerns:

* ``_SettingsModel`` (Pydantic ``BaseModel``) validates the raw values and
  provides type safety.  ``extra="ignore"`` means unknown keys in the INI file
  are silently dropped rather than raising a validation error.
* ``AppSettings`` owns the file path, reads/writes the INI, and exposes a
  clean property API.

On construction:

1. The settings directory is created if absent.
2. If the settings file does not exist, it is written with defaults.
3. The INI file is read and parsed into ``_SettingsModel``.  A
   ``ValidationError`` logs a warning and falls back to defaults.

Extending settings
------------------

To add a new persisted setting:

1. Add a field to ``_SettingsModel`` with a sensible default.
2. Add a corresponding property on ``AppSettings``.
3. Update the ``config["DEFAULT"]`` dict in ``save()`` to include the new key.
4. Update the ``cmd_settings.py`` command to expose it via the CLI.


Common layer (``common/``)
===========================

AppLocation (``common/app_location.py``)
-----------------------------------------

``AppLocation`` is a static helper that resolves three directory types:

* ``AppDir`` — the directory containing the application code.
* ``AppDataDir`` — the OS-appropriate data directory (settings, exports, …).
* ``LogDir`` — ``AppDataDir / "logs"``.

The resolution has two modes, selected automatically:

**Source tree mode** (``is_running_from_source()`` returns ``True``)
    Path contains both ``"src"`` and ``"scaldys"`` as path components.
    ``AppDataDir`` is resolved to ``<repo_root>/app_data/``, keeping all data
    local to the development checkout.

**Installed / frozen mode**
    ``get_os_app_data_path()`` is called; it returns:

    * Windows: ``%LOCALAPPDATA%\<ORGANIZATION_NAME>\<APP_NAME>\``
    * macOS: ``platformdirs.AppDirs.user_data_dir``
    * Linux: ``$HOME/.<APP_NAME>``

    When the executable is frozen by PyInstaller (``sys.frozen`` is set),
    ``sys.argv[0].parent`` is used as the app root instead of
    ``__file__.parent.parent``.

The distinction matters for tests: ``conftest.py`` patches ``AppLocation`` to
redirect all paths into a temporary directory so tests never touch the real
user data directory.

Structured logging (``common/logging.py``)
-------------------------------------------

The logging system is built on Python's ``dictConfig`` and three handlers:

.. code-block:: text

    scaldys_template logger
    ├── queue_handler  ──▶  QueueListener ──▶  file_json (RotatingFileHandler)
    ├── stdout         ──▶  filtered: DEBUG and INFO only (NonErrorFilter)
    └── stderr         ──▶  ERROR and above

**QueueHandler** (Python 3.12+) decouples the caller from disk I/O: the main
thread enqueues log records and a background thread flushes them to the JSON
Lines file.  The listener is started in ``setup_logging()`` and registered with
``atexit`` so it drains before the process exits.

**JsonFormatter** serialises each ``LogRecord`` to a JSON object.  All
``extra={}`` fields passed to the logger are automatically included in the JSON
output, making it easy to attach structured context:

.. code-block:: python

    logger.info("Processing started", extra={"num_items": 42, "timeout": 5.0})

**NonErrorFilter** ensures that WARNING and above records from the ``stdout``
handler are suppressed (they go to ``stderr`` instead), preventing duplicate
output on the console.

The ``--verbose`` flag controls whether any console output is shown at all.
Without it, only CRITICAL messages reach the console (via ``stderr``); with it,
the full log level governs what is printed to ``stdout``.

Log level semantics:

* ``off`` — no file logging; console output depends on ``--verbose``.
* ``debug`` / ``info`` / ``warning`` / ``error`` / ``critical`` — standard
  Python log levels applied to the file handler and (if ``--verbose``) the
  console handler.


Core layer (``core/``)
=======================

The ``core/`` package is intentionally thin: it contains reference
implementations that demonstrate patterns, not production code.

Async pipeline (``core/async_processor.py``)
---------------------------------------------

``process_items()`` is the public, synchronous entry point.  It wraps
``asyncio.run()`` so callers remain fully synchronous:

.. code-block:: python

    results = process_items(item_ids, on_progress=callback, timeout_per_item=5.0)

Internally, ``_run_pipeline()`` batches items in groups of ``_BATCH_SIZE``
(default 20) and processes each batch with ``asyncio.gather(return_exceptions=True)``.

Key design decisions:

* **``return_exceptions=True``** — a single failing item returns its exception
  as the result value instead of cancelling all sibling coroutines.  Every item
  gets a ``ProcessingResult`` regardless of success or failure.
* **Per-item timeout via ``asyncio.wait_for``** — a slow item is cancelled and
  reported as a timeout error without affecting the rest of the batch.
* **Batch size as the shutdown granularity** — ``_shutdown_event`` is only
  checked between batches, so the pipeline always processes the current batch
  to completion before stopping.  This trades a small delay for a clean state.
* **Progress callback protocol** — ``on_progress`` is a plain callable, not a
  dependency on Rich or any specific UI library.  The caller decides what to do
  with each result as it arrives.
* **Graceful ``KeyboardInterrupt`` handling** — caught at the ``asyncio.run()``
  boundary to avoid "Task was destroyed but it is pending!" warnings from the
  event loop teardown.

Database scaffold (``core/database.py``)
-----------------------------------------

``DatabaseConnection`` wraps a single connection behind a context manager so
``disconnect()`` is guaranteed to be called even when an exception propagates:

.. code-block:: python

    with DatabaseConnection(config) as conn:
        rows = conn.execute("SELECT * FROM items WHERE id = %s", (item_id,))

``transaction()`` is a ``@contextmanager`` that wraps a block of ``execute()``
calls in a BEGIN / COMMIT / ROLLBACK:

.. code-block:: python

    with DatabaseConnection(config) as conn:
        with transaction(conn):
            conn.execute("INSERT INTO log …", ("started",))
            conn.execute("UPDATE items …", (item_id,))

``ConnectionPool`` limits concurrent connections with a ``threading.Semaphore``
and exposes an ``acquire()`` context manager for safe checkout/checkin.

All three classes are stubs: the stub bodies log what they *would* do and
return plausible fake data.  Replace the stub bodies with your real driver
calls while keeping the same interface.


Signal Analyzer (``core/signal_*`` + ``tk/ui/`` + ``cli/commands/cmd_*``)
==========================================================================

The Signal Analyzer is the primary example application.  It demonstrates a
complete vertical slice of the template: a typed parameter model, a pure
computation engine, a non-blocking GUI, and a headless CLI command that shares
the same engine.

The dependency order is strict:

.. code-block:: text

    core/signal_model.py          ← no dependencies on GUI or CLI
    core/signal_engine.py         ← imports signal_model only
    core/parameter_store.py       ← imports signal_model + AppLocation
    tk/ui/*_frame.py              ← imports core/*  (GUI → core, never core → GUI)
    cli/commands/cmd_analyze.py   ← imports core/*  (CLI → core, never core → CLI)
    cli/commands/cmd_gui.py       ← imports tk/app  (deferred, inside function body)

The full design is documented in :ref:`signal_analyzer_dev_guide`.


Testing strategy
================

Tests are split into three categories, enforced by pytest markers:

* ``@pytest.mark.unit`` — fast, isolated tests with no filesystem or network
  I/O.  These run in every CI check.
* ``@pytest.mark.integration`` — tests that touch the filesystem or invoke
  the full CLI via ``CliRunner``.  Run in CI but excluded from "fast" local
  runs.
* ``@pytest.mark.slow`` — tests with simulated latency (e.g., the async
  pipeline with real ``asyncio.sleep`` calls).  Excluded from fast CI runs.

The test ``conftest.py`` patches ``AppLocation`` to redirect all paths into a
temporary directory, so integration tests never read or write the developer's
real user data.  A ``reset_scaldys_template_logger`` fixture in the unit ``conftest.py``
removes all handlers from the package logger after each test so logging-related
tests do not interfere with one another.


Design principles
=================

These principles guided the template's design and should guide future changes:

**Lifecycle before CLI**
    Infrastructure concerns (logging, signals, asyncio) are settled before
    Typer parses a single argument.  This means errors during startup produce
    clean log output rather than tracebacks that bypass the logging system.

**Single setup call per concern**
    ``setup_logging()`` is called exactly once, in the app callback.  The
    ``AppSettings`` INI file is written exactly once, on first run.  Duplicate
    setup calls are bugs, not idempotent operations.

**Stubs over empty files**
    ``core/`` contains working stubs rather than empty files.  A stub
    demonstrates the intended pattern, exercises the logging and path systems,
    and can be run immediately — giving a new developer something to observe
    before they start replacing the stubs with real code.

**Source tree isolation**
    When running from source (``is_running_from_source()`` returns ``True``),
    all data is written under ``<repo_root>/app_data/``.  This prevents
    development runs from polluting the user's installed-app data directory.

**Cython compatibility**
    Every file that is a candidate for Cython compilation carries
    ``# cython: language_level=3`` at the top.  This is enforced by the
    scaldys-project Cython pipeline.  Files that should not be compiled (pure
    data, config) omit the directive.
