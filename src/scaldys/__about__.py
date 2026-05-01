# -*- coding: utf-8 -*-

__all__ = [
    "APP_NAME",
    "PACKAGE_NAME",
    "ORGANIZATION_NAME",
    "VERSION",
]

from importlib.metadata import version, PackageNotFoundError

APP_NAME = "Scaldys"
PACKAGE_NAME = "scaldys"
ORGANIZATION_NAME = "Scaldys"

try:
    VERSION = version(PACKAGE_NAME)
except PackageNotFoundError:
    VERSION = "0.0.0"
