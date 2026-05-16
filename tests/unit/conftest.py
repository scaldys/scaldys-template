# -*- coding: utf-8 -*-

"""
Unit-test-specific fixtures.

These fixtures are available to all tests under tests/unit/.
They are lighter and faster than integration fixtures — no CLI invocation,
no real filesystem writes beyond what tmp_path provides.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from scaldys_template.__about__ import PACKAGE_NAME


# ---------------------------------------------------------------------------
# Logger isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_scaldys_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Restore the scaldys logger to a propagating state before each unit test.

    WHY this fixture exists
    -----------------------
    setup_logging() (tested in test_logging.py) calls dictConfig() which sets
    `propagate=False` on the scaldys logger.  This is correct for production,
    but it persists across tests in the same process because the logging module
    is global state.  Once propagate=False is set, caplog (which installs its
    handler on the root logger) stops capturing records from the scaldys logger,
    breaking any test that uses `caplog` to assert on log output.

    This autouse fixture uses monkeypatch to restore `propagate=True` before
    every unit test so caplog works reliably regardless of test ordering.
    The monkeypatch is automatically reverted after each test, so the logger
    state is consistent at the start of every test.

    This is a unit-test concern only; integration tests call setup_logging
    through the CLI and are expected to work with the real logger configuration.
    """
    monkeypatch.setattr(logging.getLogger(PACKAGE_NAME), "propagate", True)


@pytest.fixture
def sample_config_file(tmp_path: Path) -> Path:
    """
    Create a minimal YAML-like config file in a temp directory.

    Unit tests for export/process commands use this as a stand-in config
    rather than relying on a file being present in the working directory.
    The content is intentionally minimal; the export stub doesn't parse it.
    """
    config = tmp_path / "config.yml"
    config.write_text("# stub config\nversion: 1\n", encoding="utf-8")
    return config


@pytest.fixture
def sample_output_dir(tmp_path: Path) -> Path:
    """Return a path to a non-existing output directory inside tmp_path."""
    return tmp_path / "output"
