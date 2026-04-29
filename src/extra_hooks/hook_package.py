# -*- coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

# Automatically collect all submodules of the package.
# This hook is generic and derives the package name from its own filename,
# which is expected to be 'hook-<package_name>.py' after being renamed by the builder.
try:
    # Extract <package_name> from 'hook-<package_name>.py'
    # os.path.basename(__file__) -> e.g. 'hook-scaldys.py'
    _filename = os.path.basename(__file__)
    if "-" in _filename:
        _package_name = _filename.split("-", 1)[1].rsplit(".", 1)[0]
        hiddenimports = collect_submodules(_package_name)
    else:
        hiddenimports = []
except (IndexError, AttributeError):
    hiddenimports = []

# If third-party libraries are missed because they are only imported in compiled modules,
# they can be added to the hiddenimports list here.
# Example:
# hiddenimports += ['numpy', 'pandas']
