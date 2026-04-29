"""Check that basic features work.

Catch cases where e.g. files are missing so the import doesn't work. It is
recommended to check that e.g. assets are included."""

from scaldys.common.app_location import AppLocation

try:
    app_dir = AppLocation.get_directory(AppLocation.AppDir)
    if app_dir.exists() and app_dir.is_dir():
        print("Smoke test succeeded: AppDir exists.")
    else:
        raise RuntimeError(f"Smoke test failed: {app_dir} is not a valid directory.")
except Exception as e:
    raise RuntimeError(f"Smoke test failed with error: {e}")
