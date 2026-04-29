from scaldys.common.app_location import AppLocation


def test_app_location_enum():
    assert AppLocation.AppDir == 1
    assert AppLocation.AppDataDir == 2
    assert AppLocation.LogDir == 3


def test_get_directory_app_dir():
    app_dir = AppLocation.get_directory(AppLocation.AppDir)
    assert app_dir.exists()
    assert app_dir.is_dir()
