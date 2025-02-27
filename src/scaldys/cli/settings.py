# -*- coding: utf-8 -*-
# cython: language_level=3

import configparser
import logging
from pathlib import Path

from scaldys.__about__ import PACKAGE_NAME
from scaldys.common.app_location import AppLocation

__all__ = ["AppSettings"]


logger = logging.getLogger(PACKAGE_NAME)


class AppSettings:
    SETTINGS_FILE_NAME = f"{PACKAGE_NAME}_settings.ini"

    def __init__(self):
        self.log_level = None

        # internal
        self._settings_file_path = None
        self._initialize()

    def _initialize(self):
        settings_dir_path = AppLocation.get_directory(AppLocation.AppDataDir)
        if not settings_dir_path.exists():
            settings_dir_path.mkdir(parents=True)

        self._settings_file_path = Path.joinpath(settings_dir_path, self.SETTINGS_FILE_NAME)
        if not self._settings_file_path.exists():
            self.save()
        self.load()

    def load(self):
        logger.info("Loading application settings")
        config = configparser.ConfigParser()
        config.read(str(self._settings_file_path))

        try:
            # pass
            self.log_level = config["DEFAULT"]["log_level"]

        except KeyError:
            logger.debug(
                f"Not all settings keys are present in the {self.SETTINGS_FILE_NAME} file. Skipping..."
            )

    def save(self):
        logger.info("Saving application settings")

        if self._settings_file_path is None:
            logger.debug("The settings file is not defined (None). Settings not persisted...")
            return

        config = configparser.ConfigParser()
        config["DEFAULT"] = {
            "log_level": self._setting_str(self.log_level),
        }

        with self._settings_file_path.open("w") as configfile:
            config.write(configfile)

    @staticmethod
    def _setting_str(setting):
        return "" if setting is None else str(setting)
