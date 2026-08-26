"""Persistence helpers for ``SignalParameters``.

Saves / loads a ``SignalParameters`` instance as a JSON file.  The default
file location follows the existing ``AppLocation`` convention so parameters
end up alongside other application data (``app_data/`` when running from
source, ``%LOCALAPPDATA%/…`` when installed).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from scaldys_template.__about__ import PACKAGE_NAME
from scaldys_template.common.app_location import AppLocation
from scaldys_template.core.signal_model import SignalParameters

__all__ = [
    "default_parameters_path",
    "load_parameters",
    "save_parameters",
]

logger = logging.getLogger(PACKAGE_NAME)

_DEFAULT_FILENAME = "signal_parameters.json"


def default_parameters_path() -> Path:
    """Return the default path for persisted signal parameters.

    The directory is created on first use.
    """
    return AppLocation.get_directory(AppLocation.AppDataDir) / _DEFAULT_FILENAME


def save_parameters(params: SignalParameters, path: Path) -> None:
    """Serialize *params* to *path* as indented JSON.

    The parent directory is created if it does not exist.

    Parameters
    ----------
    params:
        Parameter set to persist.
    path:
        Destination file path (typically ``*.json``).

    Raises
    ------
    OSError
        If the file cannot be written.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(params.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Signal parameters saved to %s", path)
    except OSError as exc:
        logger.error("Failed to save parameters to %s: %s", path, exc)
        raise


def load_parameters(path: Path) -> SignalParameters:
    """Deserialize ``SignalParameters`` from *path*.

    Pydantic validation is applied to the loaded data, so the returned
    object is always in a valid state.

    Parameters
    ----------
    path:
        JSON file written by :func:`save_parameters`.

    Returns
    -------
    SignalParameters
        Validated parameter set.

    Raises
    ------
    OSError
        If the file cannot be read.
    pydantic.ValidationError
        If the file content fails validation.
    """
    try:
        text = path.read_text(encoding="utf-8")
        params = SignalParameters.model_validate(json.loads(text))
        logger.info("Signal parameters loaded from %s", path)
        return params
    except OSError as exc:
        logger.error("Failed to load parameters from %s: %s", path, exc)
        raise
