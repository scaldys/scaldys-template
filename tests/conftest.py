
"""
Root-level pytest configuration and shared fixtures.

Fixtures defined here are available to *all* tests (unit, integration, e2e).
Keep this file lean: only put fixtures here that are genuinely needed across
multiple test directories.  Directory-specific fixtures belong in the
corresponding subdirectory's conftest.py.

Fixture scopes used in this project
-------------------------------------
function (default) — new instance per test; safest, use unless cost is high.
module              — one instance shared within a single test file.
session             — one instance for the entire test run; use for expensive
                      setup (e.g. a real DB connection, a compiled binary).

Pytest marks registered here
------------------------------
Run selectively with:
    pytest -m unit            # fast unit tests only
    pytest -m integration     # integration tests only
    pytest -m "not slow"      # everything except slow tests
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from scaldys_template.common.app_location import AppLocation

# ---------------------------------------------------------------------------
# Mark registration
# ---------------------------------------------------------------------------
# Marks are declared in [tool.pytest.ini_options] in pyproject.toml.
# This hook adds them to the --co output and suppresses "unknown mark" warnings.


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: Fast, isolated tests with no external I/O")
    config.addinivalue_line(
        "markers", "integration: Tests that use the filesystem or invoke the CLI"
    )
    config.addinivalue_line("markers", "slow: Tests that take significant time")
    config.addinivalue_line(
        "markers", "svg: Tests that require tksvg or native Tk 8.7+ SVG support"
    )


_SVG_SUPPORT_CACHE: bool | None = None


def has_svg_support() -> bool:
    """Check if the environment supports SVG images (tksvg or Tk 8.7+)."""
    global _SVG_SUPPORT_CACHE
    if _SVG_SUPPORT_CACHE is not None:
        return _SVG_SUPPORT_CACHE

    try:
        import tksvg  # type: ignore[import-not-found]

        if tksvg is not None:
            _SVG_SUPPORT_CACHE = True
            return True
    except ImportError:
        pass

    # No tksvg. Check for native Tk 8.7+ SVG support
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        # Try to create a small dummy SVG image
        dummy_svg = (
            '<svg width="1" height="1" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="1" height="1" fill="black"/></svg>'
        )
        tkinter.PhotoImage(master=root, data=dummy_svg, format="svg")
        root.destroy()
        _SVG_SUPPORT_CACHE = True
        return True
    except (tkinter.TclError, RuntimeError, ImportError):
        _SVG_SUPPORT_CACHE = False
        return False


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests marked with 'svg' if SVG support is missing."""
    if any(mark.name == "svg" for mark in item.iter_markers()) and not has_svg_support():
        pytest.skip("SVG support (tksvg or Tk 8.7+) is not available")


# ---------------------------------------------------------------------------
# Keystone fixture: isolated_app_location
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_app_location(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[int, Path]:
    """
    Redirect all AppLocation paths to temporary directories for the duration
    of one test.

    WHY this fixture exists
    -----------------------
    `AppLocation.get_directory` returns OS-specific paths (e.g.
    %LOCALAPPDATA%\\Scaldys\\Scaldys on Windows).  Without redirection,
    tests that instantiate AppSettings, call setup_logging, or run CLI commands
    would write real files to the developer's or CI machine's app-data folder.
    This fixture ensures every test is hermetic: all file I/O goes to a
    per-test tmp directory that pytest cleans up automatically.

    Usage
    -----
        def test_something(isolated_app_location):
            # AppLocation now returns tmp paths for this test only.
            settings = AppSettings()   # reads/writes to tmp dir
            setup_logging("info")      # log file goes to tmp dir

    Returns
    -------
    dict mapping AppLocation constants → Path
        {AppLocation.AppDir: <tmp>/app,
         AppLocation.AppDataDir: <tmp>/app_data,
         AppLocation.LogDir: <tmp>/logs}
    """
    dirs: dict[int, Path] = {
        AppLocation.AppDir: tmp_path / "app",
        AppLocation.AppDataDir: tmp_path / "app_data",
        AppLocation.LogDir: tmp_path / "logs",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    def _mock_get_directory(dir_type: int) -> Path:
        if dir_type not in dirs:
            raise ValueError(f"Unknown directory type: {dir_type}")
        return dirs[dir_type]

    monkeypatch.setattr(AppLocation, "get_directory", staticmethod(_mock_get_directory))
    return dirs


# ---------------------------------------------------------------------------
# Legacy fixtures — kept for backwards compatibility
# ---------------------------------------------------------------------------
# These were present in the original conftest.py.  New tests should use
# pytest's built-in `tmp_path` fixture instead of `temporary_test_directory`.


@pytest.fixture(scope="session")
def temporary_test_directory(tmpdir_factory) -> str:
    """Session-scoped temporary directory (legacy; prefer pytest's tmp_path)."""
    timestamp = f"{datetime.datetime.now(datetime.UTC):%Y-%m-%d_%H-%M-%S}"
    return str(tmpdir_factory.mktemp(f"testrun-{timestamp}", numbered=False))


@pytest.fixture(scope="session", autouse=True)
def setup_test_data_if_not_exist() -> None:
    """
    Session-level setup hook.  Add global test-data preparation here if needed.
    Stub: currently a no-op.  Kept as a template for projects that need
    database seeding, fixture-file generation, etc. before any test runs.
    """
