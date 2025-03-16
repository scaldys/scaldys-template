# -*- coding: utf-8 -*-
# cython: language_level=3

import logging
import os
import sys
import platform

from pathlib import Path

import platformdirs

from scaldys.__about__ import APP_NAME, PACKAGE_NAME, ORGANIZATION_NAME

__all__ = ["AppLocation"]


logger = logging.getLogger(PACKAGE_NAME)

APP_PATH = Path(__file__).parent.parent
FROZEN_APP_PATH = Path(sys.argv[0]).parent


class AppLocation:
    """
    AppLocation is a static class which retrieves a directory based on the directory type.
    """

    AppDir = 1
    AppDataDir = 2
    LogDir = 3

    @staticmethod
    def get_directory(dir_type: int = AppDir) -> Path:
        """
        Return the directory path for the specified application directory type.

        Parameters
        ----------
        dir_type : int, default 'AppDir'
            The directory type you want.

        Returns
        -------
        Path
            The requested path.

        Raises
        ------
        ValueError
            If unknown application directory type.
        """
        app_path = FROZEN_APP_PATH if is_frozen() else APP_PATH
        if is_running_from_source(app_path):
            app_data_path = app_path.parent.parent.joinpath("app_data")
        else:
            app_data_path = get_os_app_data_path()

        if dir_type == AppLocation.AppDir:
            path = app_path
        elif dir_type == AppLocation.AppDataDir:
            path = app_data_path
        elif dir_type == AppLocation.LogDir:
            path = app_data_path.joinpath("logs")
        else:
            raise ValueError(f"Unknown directory type: {dir_type}")

        logger.debug(f"Path: {path}")
        logger.debug(f"Frozen App Path: {FROZEN_APP_PATH}")
        logger.debug(f"App Path: {APP_PATH}")
        logger.debug(f"App DataPath: {app_data_path}")

        return path.resolve()


def is_frozen() -> bool:
    """
    Test whether the application is frozen or not.

    Returns
    -------
    bool
        True if frozen, False otherwise.

    """
    return getattr(sys, "frozen", False)


def get_os_app_data_path() -> Path:
    """
    Return an application specific path for the operating system.

    Returns
    -------
    Path
        The requested path.
    """
    dirs = platformdirs.AppDirs(APP_NAME, multipath=True)

    if platform.system() == "Windows":
        app_data_dir = os.getenv("LOCALAPPDATA")
        # os.getenv() can return None; LOCALAPPDATA is a Windows system variable and shall exist (so PyRight is happy).
        assert app_data_dir is not None
        app_data_path = Path(app_data_dir, ORGANIZATION_NAME, APP_NAME)
    elif platform.system() == "Darwin":
        app_data_path = Path(dirs.user_data_dir)
    else:
        app_data_dir = os.getenv("HOME")
        # os.getenv() can return None; HOME is a system variable and shall exist (so PyRight is happy).
        assert app_data_dir is not None
        app_data_path = Path(app_data_dir, f".{APP_NAME}")

    return app_data_path


def is_running_from_source(app_path: Path) -> bool:
    """
    Test whether the program running from the source tree, based on the path of the script file.

    Parameters
    ----------
    app_path: Path
        The path

    Returns
    -------
    bool
        True if the program is running from the source tree, False otherwise.
    """
    return f"src\\{PACKAGE_NAME}" in str(app_path.resolve())
