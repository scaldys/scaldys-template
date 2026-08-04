# -*- coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules, copy_metadata, collect_data_files

# Automatically collect all submodules, dist-info metadata and data files for the package.
# This hook is generic and derives the package name from its own filename,
# which is expected to be 'hook-<package_name>.py' after being renamed by the builder.
# The dist-info metadata is required so that importlib.metadata.version() works
# inside the frozen executable (used by __about__.py).
try:
    # Extract <package_name> from 'hook-<package_name>.py'
    # os.path.basename(__file__) -> e.g. 'hook-scaldys.py'
    _filename = os.path.basename(__file__)
    if "-" in _filename:
        _package_name = _filename.split("-", 1)[1].rsplit(".", 1)[0]
        hiddenimports = collect_submodules(_package_name)
        datas = copy_metadata(_package_name) + collect_data_files(_package_name)
    else:
        hiddenimports = []
        datas = []
except (IndexError, AttributeError):
    hiddenimports = []
    datas = []

# If third-party libraries are missed because they are only imported in compiled modules,
# they can be added to the hiddenimports list here.
# Example:
# hiddenimports += ['numpy', 'pandas']
