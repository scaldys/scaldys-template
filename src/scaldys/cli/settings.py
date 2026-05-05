# -*- coding: utf-8 -*-

import configparser
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from scaldys.__about__ import PACKAGE_NAME
from scaldys.common.app_location import AppLocation

__all__ = ["AppSettings"]


logger = logging.getLogger(PACKAGE_NAME)

# Valid log-level strings accepted by the CLI; empty string means "not configured"
_LogLevel = Literal["off", "debug", "info", "warning", "error", "critical", ""]


class _SettingsModel(BaseModel):
    log_level: _LogLevel = ""

    model_config = {"extra": "ignore"}


class AppSettings:
    SETTINGS_FILE_NAME = f"{PACKAGE_NAME}_settings.ini"

    def __init__(self):
        self._settings_file_path: Path | None = None
        self._model: _SettingsModel = _SettingsModel()
        self._initialize()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def log_level(self) -> str | None:
        value = self._model.log_level
        return value if value else None

    @log_level.setter
    def log_level(self, value: str | None) -> None:
        self._model = _SettingsModel(log_level=value or "")

    def save(self) -> None:
        logger.debug("Saving application settings")
        if self._settings_file_path is None:
            logger.debug("The settings file is not defined (None). Settings not persisted...")
            return
        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "log_level": self._model.log_level,
        }
        with self._settings_file_path.open("w") as configfile:
            config.write(configfile)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        settings_dir = AppLocation.get_directory(AppLocation.AppDataDir)
        if not settings_dir.exists():
            settings_dir.mkdir(parents=True)

        self._settings_file_path = settings_dir / self.SETTINGS_FILE_NAME
        if not self._settings_file_path.exists():
            self.save()

        logger.info("Loading application settings")

        config = configparser.ConfigParser()
        config.read(str(self._settings_file_path))
        raw: dict[str, Any] = {}
        try:
            raw = dict(config["DEFAULT"])
        except KeyError:
            pass

        try:
            self._model = _SettingsModel(**raw)
        except ValidationError as exc:
            logger.warning(
                f"Invalid settings in {self.SETTINGS_FILE_NAME}: {exc}. Using defaults."
            )
            self._model = _SettingsModel()
