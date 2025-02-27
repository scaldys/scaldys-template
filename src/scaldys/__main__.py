# -*- coding: utf-8 -*-
# cython: language_level=3

import logging
from scaldys.__about__ import PACKAGE_NAME

from scaldys.common.app_logging import setup_logging

__all__ = ["hello"]


# https://github.com/mCodingLLC/VideosSampleCode/tree/master/videos/135_modern_logging
# use <application_name> in all files for the logger
# __name__ is another common choice, but would create multiple equivalent instances in memory
logger = logging.getLogger(PACKAGE_NAME)


def hello(n: int) -> str:
    """Greet the sum from 0 to n (exclusive end)."""
    sum_n = sum(range(n))
    return f"Hello {sum_n}!"


def main():
    setup_logging(level="debug", verbose=True)
    logging.basicConfig(level="INFO")
    logger.debug("debug message", extra={"x": "hello"})
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")

    try:
        division_by_zero = 1 / 0
        print(division_by_zero)
    except ZeroDivisionError:
        logger.exception("exception message")


if __name__ == "__main__":
    main()
