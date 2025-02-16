# -*- coding: utf-8 -*-
# cython: language_level=3

import os
import sys

from typing import Optional

try:
    from distro import id as distro_id
except ImportError:
    # The distro module is only valid for Linux, so if it doesn't exist, create a function that always returns False
    def distro_id():
        return False


__all__ = ["is_win", "is_macosx", "is_linux"]


def is_win() -> bool:
    """Test whether running on a system with a nt kernel e.g. Windows, Wine

    Returns
    -------
    bool:
        True if system is running a nt kernel, False otherwise
    """
    return os.name.startswith("nt")


def is_macosx() -> bool:
    """Test whether running on a system with a darwin kernel e.g. Mac OS X

    Returns
    -------
    bool:
        True if system is running a darwin kernel, False otherwise
    """
    return sys.platform.startswith("darwin")


def is_linux(distro: Optional[str] = None) -> bool:
    """Test whether running on a system with a linux kernel e.g. Ubuntu, Debian, etc

    Parameters
    ----------
    distro: str, optional
        If not None, check if running that Linux distro

    Returns
    -------
    bool:
        True if system is running a linux kernel, False otherwise
    """
    result = sys.platform.startswith("linux")
    if result and distro:
        result = result and distro == distro_id()
    return result
