from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# Automatically collect all submodules, dist-info metadata and data files for the package.
# The dist-info metadata is required so that importlib.metadata.version() works
# inside the frozen executable (used by __about__.py).

_package_name = "scaldys_template"

hiddenimports = collect_submodules(_package_name)
datas = copy_metadata(_package_name) + collect_data_files(_package_name)

# If third-party libraries are missed because they are only imported in compiled modules,
# they can be added to the hiddenimports list here.
# Example:
# hiddenimports += ['numpy', 'pandas']
