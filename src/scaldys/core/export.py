# -*- coding: utf-8 -*-
# cython: language_level=3
import json
import logging

from pathlib import Path

from scaldys.__about__ import PACKAGE_NAME

logger = logging.getLogger(f"{PACKAGE_NAME}")

__all__ = ["export_data"]


def export_data(config_file_path: Path, output_dir_path: Path, num_values: int) -> None:
    """Implementation of the exportation of data."""

    # implement data export logic here
    file_name = "data.json"

    try:
        # Ensure the parent directory exists
        output_dir_path = output_dir_path.resolve()
        output_dir_path.mkdir(parents=True, exist_ok=True)
        file_path = output_dir_path / file_name
        logger.debug(f"Output file: {file_path}")

        data = {f"key_{n}": n * 2 for n in range(num_values)}

        # Write dictionary to file in JSON format
        with file_path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=4, ensure_ascii=False)

        logger.info(f"Data successfully exported to {file_path}")
    except Exception as e:
        logger.error(f"Failed to export data to {file_name}: {e}")
        raise
