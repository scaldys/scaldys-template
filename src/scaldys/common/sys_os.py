# -*- coding: utf-8 -*-
# cython: language_level=3

import platform


__all__ = ["is_win", "is_macosx", "is_linux"]


def is_win() -> bool:
    """Test whether running on a system with a nt kernel e.g. Windows, Wine

    Returns
    -------
    bool:
        True if system is running a nt kernel, False otherwise
    """
    return platform.system() == "Windows"


def is_macosx() -> bool:
    """Test whether running on a system with a darwin kernel e.g. Mac OS X

    Returns
    -------
    bool:
        True if system is running a darwin kernel, False otherwise
    """
    return platform.system() == "Darwin"


def is_linux() -> bool:
    """Test whether running on a system with a linux kernel e.g. Ubuntu, Debian, etc

    Returns
    -------
    bool:
        True if system is running a linux kernel, False otherwise
    """
    return platform.system() == "Linux"
