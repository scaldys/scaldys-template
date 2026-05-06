# -*- coding: utf-8 -*-

"""
Unit tests for scaldys.cli.settings (AppSettings).

Patterns demonstrated
----------------------
- All tests use isolated_app_location so no real OS paths are touched.
- caplog fixture to assert that warning messages are emitted on bad settings.
- Testing save + reload round-trip to verify persistence.
- pytest.raises with pydantic ValidationError.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest
from pydantic import ValidationError

from scaldys.cli.settings import AppSettings


# ---------------------------------------------------------------------------
# Default state
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppSettingsDefaults:
    def test_log_level_is_none_when_unset(self, isolated_app_location):
        settings = AppSettings()
        assert settings.log_level is None

    def test_settings_file_is_created_on_first_run(self, isolated_app_location):
        """Constructing AppSettings must create the settings INI file."""
        data_dir = isolated_app_location[2]  # AppLocation.AppDataDir == 2
        settings = AppSettings()
        ini_files = list(data_dir.glob("*.ini"))
        assert len(ini_files) == 1


# ---------------------------------------------------------------------------
# Getter / setter
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppSettingsLogLevel:
    @pytest.mark.parametrize("level", ["off", "debug", "info", "warning", "error", "critical"])
    def test_set_valid_log_level(self, isolated_app_location, level: str):
        settings = AppSettings()
        settings.log_level = level
        assert settings.log_level == level

    def test_set_none_clears_log_level(self, isolated_app_location):
        settings = AppSettings()
        settings.log_level = "debug"
        settings.log_level = None
        assert settings.log_level is None

    def test_set_invalid_log_level_raises_validation_error(self, isolated_app_location):
        settings = AppSettings()
        with pytest.raises(ValidationError):
            settings.log_level = "verbose"  # not a valid level

    def test_set_empty_string_clears_log_level(self, isolated_app_location):
        settings = AppSettings()
        settings.log_level = "debug"
        settings.log_level = ""
        assert settings.log_level is None


# ---------------------------------------------------------------------------
# Persistence (save / reload)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppSettingsPersistence:
    def test_save_and_reload_preserves_log_level(self, isolated_app_location):
        """Setting a level, saving, then constructing a new AppSettings must
        return the same level."""
        s1 = AppSettings()
        s1.log_level = "warning"
        s1.save()

        s2 = AppSettings()
        assert s2.log_level == "warning"

    def test_save_writes_ini_file(self, isolated_app_location):
        data_dir = isolated_app_location[2]
        settings = AppSettings()
        settings.log_level = "error"
        settings.save()

        # Verify the raw INI content contains the level we set.
        ini_path = data_dir / AppSettings.SETTINGS_FILE_NAME
        config = configparser.ConfigParser()
        config.read(str(ini_path))
        assert config["DEFAULT"].get("log_level") == "error"


# ---------------------------------------------------------------------------
# Resilience: corrupted or invalid settings file
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppSettingsResilience:
    def test_corrupted_settings_falls_back_to_defaults(
        self, isolated_app_location, caplog: pytest.LogCaptureFixture
    ):
        """An INI file with an invalid log_level should log a warning and
        fall back to default (log_level = None)."""
        data_dir = isolated_app_location[2]
        ini_path = data_dir / AppSettings.SETTINGS_FILE_NAME

        # Write a settings file with an invalid log_level value.
        ini_path.write_text("[DEFAULT]\nlog_level = totally_invalid\n", encoding="utf-8")

        import logging

        with caplog.at_level(logging.WARNING, logger="scaldys"):
            settings = AppSettings()

        assert settings.log_level is None
        assert any("Invalid settings" in r.message for r in caplog.records), (
            "Expected a warning about invalid settings"
        )

    def test_missing_settings_file_creates_new_one(self, isolated_app_location):
        data_dir = isolated_app_location[2]
        ini_path = data_dir / AppSettings.SETTINGS_FILE_NAME
        assert not ini_path.exists()

        AppSettings()  # should create the file
        assert ini_path.exists()
