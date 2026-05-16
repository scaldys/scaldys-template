# -*- coding: utf-8 -*-

"""
Unit tests for scaldys.common.app_location.

Patterns demonstrated
----------------------
- @pytest.mark.parametrize to cover multiple dir types in one test
- pytest.raises to assert exception type and message
- monkeypatch to control platform and sys state
- @pytest.mark.skipif for platform-specific tests
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scaldys_template.common.app_location import (
    AppLocation,
    is_frozen,
    is_running_from_source,
    get_os_app_data_path,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppLocationConstants:
    """The integer constants must not change — code elsewhere relies on them."""

    def test_app_dir_value(self):
        assert AppLocation.AppDir == 1

    def test_app_data_dir_value(self):
        assert AppLocation.AppDataDir == 2

    def test_log_dir_value(self):
        assert AppLocation.LogDir == 3


# ---------------------------------------------------------------------------
# get_directory
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetDirectory:
    """Tests for AppLocation.get_directory using the isolated_app_location fixture."""

    @pytest.mark.parametrize(
        "dir_type",
        [
            AppLocation.AppDir,
            AppLocation.AppDataDir,
            AppLocation.LogDir,
        ],
    )
    def test_returns_path_instance(self, isolated_app_location: dict, dir_type: int):
        result = AppLocation.get_directory(dir_type)
        assert isinstance(result, Path)

    @pytest.mark.parametrize(
        "dir_type",
        [
            AppLocation.AppDir,
            AppLocation.AppDataDir,
            AppLocation.LogDir,
        ],
    )
    def test_returns_existing_directory(self, isolated_app_location: dict, dir_type: int):
        result = AppLocation.get_directory(dir_type)
        assert result.exists()
        assert result.is_dir()

    def test_invalid_type_raises_value_error(self, isolated_app_location: dict):
        with pytest.raises(ValueError, match="Unknown directory type"):
            AppLocation.get_directory(99)

    def test_each_dir_type_returns_distinct_path(self, isolated_app_location: dict):
        """All three directory types must resolve to different paths."""
        paths = [
            AppLocation.get_directory(AppLocation.AppDir),
            AppLocation.get_directory(AppLocation.AppDataDir),
            AppLocation.get_directory(AppLocation.LogDir),
        ]
        assert len(set(str(p) for p in paths)) == 3


# ---------------------------------------------------------------------------
# is_frozen
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsFrozen:
    def test_not_frozen_in_normal_runtime(self):
        # Running under pytest: sys.frozen is not set.
        assert is_frozen() is False

    def test_frozen_when_sys_frozen_is_true(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        assert is_frozen() is True

    def test_not_frozen_when_sys_frozen_is_false(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(sys, "frozen", False, raising=False)
        assert is_frozen() is False


# ---------------------------------------------------------------------------
# is_running_from_source
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsRunningFromSource:
    @pytest.mark.parametrize(
        "path_str, expected",
        [
            # Typical source-tree execution: must contain both "src" AND "scaldys_template"
            (r"C:\Dev\scaldys-template\src\scaldys_template\common", True),
            ("/home/user/projects/scaldys-template/src/scaldys_template/common", True),
            # Installed package — no "src" component
            (r"C:\Users\user\AppData\Local\Programs\scaldys_template", False),
            ("/usr/local/lib/python3.13/site-packages/scaldys_template", False),
            # Has "src" but not PACKAGE_NAME ("scaldys_template")
            ("/home/user/src/other_package/common", False),
        ],
    )
    def test_parametrized_paths(self, path_str: str, expected: bool):
        assert is_running_from_source(Path(path_str)) is expected


# ---------------------------------------------------------------------------
# get_os_app_data_path — platform-specific
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetOsAppDataPath:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific path logic")
    def test_windows_uses_localappdata(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\testuser\AppData\Local")
        result = get_os_app_data_path()
        assert "Scaldys" in result.parts or "scaldys_template" in str(result).lower()

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific path logic")
    def test_windows_raises_if_localappdata_missing(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        with pytest.raises(RuntimeError, match="LOCALAPPDATA"):
            get_os_app_data_path()

    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific path logic")
    def test_linux_uses_home(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("HOME", "/tmp/fakehome")
        result = get_os_app_data_path()
        assert "/tmp/fakehome" in str(result)
