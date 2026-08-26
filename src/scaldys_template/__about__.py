
__all__ = [
    "APP_NAME",
    "ORGANIZATION_NAME",
    "PACKAGE_NAME",
    "VERSION",
]

from importlib.metadata import PackageNotFoundError, version

APP_NAME = "Scaldys-Template"
PACKAGE_NAME = "scaldys_template"
ORGANIZATION_NAME = "Scaldys"

try:
    VERSION = version(PACKAGE_NAME)
except PackageNotFoundError:
    VERSION = "0.0.0"
