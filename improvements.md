# Scaldys Source Code Analysis Report

## Overview

The `src/scaldys` package is a well-structured Python application designed with
modularity and cross-platform compatibility in mind. It uses modern libraries
like `typer` for CLI management, `pathlib` for path manipulations, and
structured logging for observability.

## Architectural Components

### 1. CLI Layer (`src/scaldys/cli`)

- **Framework**: Built using `typer`, providing a robust and type-hinted
  command-line interface.
- **Organization**: Commands are separated into individual modules
  (`cmd_export.py`, `cmd_settings.py`), promoting maintainability.
- **Shared Types**: `arg_types.py` defines reusable `Annotated` types for CLI
  options, ensuring consistency across commands.

### 2. Core Logic (`src/scaldys/core`)

- **Separation of Concerns**: Business logic like data export is isolated in the
  `core` package, independent of the CLI implementation.
- **Data Export**: `export_data` handles JSON serialization and directory
  management.

### 3. Common Utilities (`src/scaldys/common`)

- **Path Management**: `AppLocation` provides a centralized way to determine
  application directories (App, Data, Logs) across Windows, macOS, and Linux. It
  correctly handles "frozen" (compiled) vs. source execution.
- **Logging System**: A sophisticated logging setup in `logging.py` featuring:
  - Structured JSON output (JSON Lines format).
  - Asynchronous logging using `QueueHandler` and `QueueListener` (Python 3.12+
    style).
  - Console and file handlers with level-based filtering.
  - Custom `JsonFormatter` for consistent log records.

### 4. Configuration (`src/scaldys/cli/settings.py`)

- **Persistence**: `AppSettings` manages application-wide settings using
  `configparser` (`.ini` files), stored in OS-specific app data folders.

## Technical Observations

- **Cython Compatibility**: Files include `# cython: language_level=3`
  directives and `__init__.py` is designed to facilitate compilation via
  `compile.py`.
- **Platform Sensitivity**: `app_location.py` specifically addresses
  Windows-specific environment variables (`LOCALAPPDATA`) and Darwin/Linux
  standards.
- **Logging Design**: The use of `QueueHandler` ensures that logging operations
  do not block the main execution thread, which is excellent for performance.

## Previously Fixed Issues

1.  ~~**Robustness in Path Detection**: In `app_location.py`, the
    `is_running_from_source` check relies on a hardcoded string `src\\scaldys`.
    Using `pathlib` parts or a more platform-agnostic check would be safer.~~
    **Fixed**: Now uses `Path.parts` to check for `"src"` and `PACKAGE_NAME` as
    individual path components, which is platform-agnostic.
2.  ~~**Configuration Schema**: The current `AppSettings` in `settings.py` reads
    values from a `.ini` file using `configparser` and stores them as raw
    strings. Every value is silently treated as a string, so an invalid
    `log_level` would be accepted without complaint and only fail later.~~
    **Fixed**: Replaced `configparser`-only approach with a `pydantic`
    `BaseModel` (`_SettingsModel`) that validates `log_level` against a
    `Literal` of the accepted values. The `.ini` file format on disk is
    unchanged (no migration needed). Invalid settings at load time now log a
    warning and fall back to defaults instead of silently passing through.
3.  ~~**Hardcoded Logic**: In `cmd_export.py`, there is a hardcoded increment
    `num_values += 10`. If this is intentional for padding, it should be
    documented or made a configurable parameter.~~ **Fixed**: Removed the
    spurious `num_values += 10` line — it was an accidental leftover with no
    intended purpose.
4.  ~~**Error Handling**: Some areas use broad `Exception` catches. Narrowing
    these to specific errors (e.g., `OSError`, `json.JSONDecodeError`) would
    improve diagnostic clarity.~~ **Fixed**: The `except Exception` in
    `core/export.py` now catches `OSError` specifically — the only realistic
    failure from `mkdir`, `open`, and `json.dump` on a plain dict.
5.  ~~**Type Consistency**: While type hints are used, adding a `py.typed` file
    would allow users of the package to benefit from static type checking if
    it's ever used as a library.~~ **Fixed**: Added an empty
    `src/scaldys/py.typed` marker file (PEP 561) and declared it under
    `[tool.setuptools.package-data]` in `pyproject.toml` so it is included in
    the distribution.

## Suggested Improvements

6.  ~~**Assertion Used for Input Validation (`logging.py:56`)**: `setup_logging`
    validates the `level` argument with `assert level.lower() in [...]`. Python
    `assert` statements are stripped when the interpreter runs with the `-O`
    (optimize) flag, meaning this guard silently disappears in optimized builds.
    Replace with an explicit `if`/`raise ValueError(...)` check to guarantee the
    validation is always enforced regardless of the run mode.~~ **Fixed**:
    Replaced the `assert` with an explicit `if`/`raise ValueError(...)` guard.
    The docstring `Raises` section was also updated from `AssertionError` to
    `ValueError`.

7.  ~~**Double Logging Initialisation (`__main__.py:17`, `cmd_export.py:67`)**:
    `main()` in `__main__.py` calls `setup_logging(level="debug", verbose=True)`
    unconditionally, then `app()` is called, and the `export` command calls
    `setup_logging` a second time with the user-provided parameters. Each call
    to `setup_logging` runs `dictConfig` (creating a fresh `QueueHandler`) and
    registers the queue listener via `atexit.register`. The first listener is
    registered but never replaced, leading to a listener for a stale handler
    being stopped at exit. Remove the `setup_logging` and `logging.basicConfig`
    calls from `main()` in `__main__.py`; let the individual commands own
    logging initialisation as they already do.~~ **Fixed**: Moved `--log` /
    `--verbose` from individual commands to the Typer **app-level callback** in
    `cli.py`. `setup_logging` is now called exactly once, before any subcommand
    runs, using the user-supplied flags (falling back to `AppSettings.log_level`
    if omitted). Individual commands no longer call `setup_logging`.
    `__main__.py` has been rewritten as a proper lifecycle entry point
    (freeze_support, pre-init logging fallback, crash hook, signal handlers,
    asyncio policy, environment validation) — it installs these concerns before
    handing off to `app()`. The `pyproject.toml` entry point was updated from
    `scaldys.cli.cli:app` to `scaldys.__main__:main` so the lifecycle setup runs
    for all CLI invocations.

8.  ~~**Unused Import and Dead Module-Level Variable (`cmd_export.py:4,22`)**:~~

    ```python
    `from datetime import datetime, timedelta, date, time` and
    `next_day = datetime.combine(date.today() + timedelta(days=1), time(0))`
    ```

    ~~`next_day` is computed at module import time but never referenced anywhere
    in the file. This is also a hidden side-effect on import. Both the import
    and the assignment should be deleted.~~ **Fixed**: Removed the unused
    `from datetime import ...` line and the dead `next_day` module-level
    assignment from `cmd_export.py`.

9.  ~~**Module-Level Side-Effect in Default Argument (`cmd_export.py:49-51`)**:
    The default value for `output_dir` in the `export` function signature is:~~

    ```python
    output_dir: ARG_TYPE_OUTPUT_PATH = AppLocation.get_directory(AppLocation.AppDataDir).joinpath("data_export"),
    ```

    ~~Default argument expressions are evaluated once at function-definition
    time (i.e., on module import). This triggers `AppLocation.get_directory()`,
    which calls `logger.debug()` before logging has been configured. It also
    means the path is computed once and cached, so it never reflects a changed
    environment after startup. Use `None` as the sentinel default and resolve
    the directory inside the function body instead.~~ **Fixed**: Changed the
    `output_dir` default to `None` and moved the `AppLocation.get_directory()`
    call into the function body, so it runs after logging is configured and
    always reflects the current environment.

10. ~~**Help Text Inconsistency for `--log` Option (`arg_types.py:24`)**: The
    help string for `ARG_TYPE_LOG_LEVEL` lists `"warn"` as a valid value:~~

    > "Set the log level (off, debug, info, **warn**, error, critical)"

    ~~The actual valid value accepted by `setup_logging` and validated by
    `_SettingsModel._LogLevel` is `"warning"`. Passing `"warn"` would be
    silently treated as an invalid level (it would bypass the
    `pydantic`/`assert` validation and fail unpredictably). Fix the help text to
    say `"warning"` instead of `"warn"`.~~ **Fixed**: Changed `"warn"` to
    `"warning"` in the `ARG_TYPE_LOG_LEVEL` help string so it matches the actual
    accepted value.

11. ~~**`settings log` Accepts Any String Without Validation
    (`cmd_settings.py:41`)**: The `log` command takes a raw `str` argument and
    writes it directly to settings with no validation at the CLI layer:~~

    ```python
    def log(level: ARG_TYPE_LOG_LEVEL) -> None:
        settings = AppSettings()
        settings.log_level = level   # Pydantic validates here, but raises silently
    ```

    ~~An invalid value will raise a `ValidationError` inside
    `AppSettings.log_level.setter` (via
    `_SettingsModel(log_level=value or "")`), which is currently uncaught and
    will produce an unformatted traceback to the user. Use
    `typer.Argument(..., show_choices=True)` with `click.Choice` or add an
    explicit guard to give the user a friendly error message before
    persisting.~~ **Fixed**: Added an explicit `try/except ValidationError`
    guard around the `settings.log_level = level` assignment. On an invalid
    value, the command now prints a friendly
    `"Error: '...' is not a valid log level"` message to stderr and exits with
    code 1 instead of leaking an unformatted pydantic traceback.

12. ~~**Incorrect/Overly Broad Dependency in `pyproject.toml`**:
    `pydantic-settings>=2.0` is listed as a runtime dependency, but the code
    only imports `pydantic.BaseModel` and `pydantic.ValidationError` — the
    `pydantic-settings` extension package (which provides `BaseSettings`,
    env-file loading, etc.) is never used. Replace `pydantic-settings>=2.0` with
    `pydantic>=2.0` to avoid pulling in the unnecessary extra package and its
    own transitive dependencies (`python-dotenv`, etc.).~~ **Fixed**: Replaced
    `pydantic-settings>=2.0` with `pydantic>=2.0` in `pyproject.toml`
    dependencies.

13. ~~**`NonErrorFilter` Docstring Inaccuracy (`logging.py:248-254`)**: The
    class docstring stated it "exclude[s] log records containing error-level
    messages", but the implementation is:~~

    ```python
    return record.levelno <= logging.INFO
    ```

    ~~This also suppresses `WARNING` (level 30), not just `ERROR`/`CRITICAL`.
    The docstring should accurately say the filter passes only `DEBUG` and
    `INFO` records, suppressing `WARNING` and above.~~ **Fixed**: Updated the
    `NonErrorFilter` docstring to accurately state it "passes only DEBUG and
    INFO records, suppressing WARNING and above."

14. ~~**`assert` Used for Environment Variable Checks
    (`app_location.py:102,109`)**: Two locations use
    `assert app_data_dir is not None` to satisfy PyRight after `os.getenv()`
    calls. As noted in item 6, `assert` is stripped under `-O`. The comment
    already acknowledges PyRight; use explicit guards
    (`if app_data_dir is None: raise RuntimeError(...)`) or use a non-`None`
    default in `os.getenv("LOCALAPPDATA", "")` combined with a truthiness check
    to make the validation optimization-proof.~~ **Fixed**: Replaced both
    `assert app_data_dir is not None` statements with explicit
    `if app_data_dir is None: raise RuntimeError(...)` guards. The stale
    PyRight-appeasement comments were also removed.

15. ~~**Unused `config_file_path` Parameter in `export_data`
    (`core/export.py:16`)**: The `config_file_path` parameter is accepted by
    `export_data` and documented as "currently unused, reserved for future use",
    but it is never accessed inside the function. Carrying unused parameters
    across call sites creates misleading API surface. Either implement it, or
    remove it from the signature and call sites until it has a concrete use.~~
    **Fixed** by using the unused parameter. export_date() serves only as an
    example.

16. ~~**Dead Code in `conftest.py` (`tests/conftest.py:23-27`)**: The
    `setup_test_data_if_not_exist` fixture is `autouse=True` but contains only a
    `print` statement and no setup/teardown logic. The
    `temporary_test_directory` fixture is defined but referenced by no test.
    Remove both unused fixtures to avoid confusing future contributors into
    thinking pre-test setup is happening when it is not.~~ **Leave as is**. This
    is a stub/template function that can be used as a starting point for future
    tests.

17. ~~**Namespace Pollution from `__init__.py` Star-Import
    (`src/scaldys/__init__.py:3`)**:~~
    ```python
    from scaldys.__main__ import *
    ```
    ~~`__main__.py` defines no `__all__`, so this re-exports every name at
    module scope including `logging`, `PACKAGE_NAME`, `setup_logging`, `app`,
    and `main`. This makes `scaldys.logging`, `scaldys.app`, etc. valid
    (unintended) public names. Either add `__all__ = []` to `__main__.py` if
    nothing should be exported, or remove the star-import from `__init__.py`
    entirely, since `__main__.py` is an entry point, not a library
    module.~~**Fixed** by adding `__all__ = []` to `__main__.py`.
