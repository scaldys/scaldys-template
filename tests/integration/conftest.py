# -*- coding: utf-8 -*-

"""
Integration-test fixtures.

Fixtures here extend the root conftest.py fixtures with integration-specific
concerns: real CLI runner instances, larger setup for filesystem tests, etc.

Scope reminder
--------------
- Use `scope="module"` for the CliRunner because it is stateless — one instance
  shared within a test file costs nothing extra.
- Use `scope="function"` (default) for `isolated_app_location` (defined in root
  conftest.py) because each integration test must start with a clean slate.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


@pytest.fixture(scope="module")
def cli_runner() -> CliRunner:
    """
    A CliRunner with separated stdout/stderr streams.

    Using mix_stderr=False lets integration tests independently assert on
    normal output (result.output) and error output (result.stderr — accessible
    via result.stderr if using Typer's CliRunner).

    Note: The CliRunner runs the app in-process (same Python interpreter),
    so monkeypatched fixtures like isolated_app_location work correctly.
    For true out-of-process testing (subprocess), use the subprocess module
    or a dedicated e2e test framework instead.
    """
    return CliRunner()
