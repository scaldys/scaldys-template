# -*- coding: utf-8 -*-
# cython: language_level=3
import logging.config
import logging.handlers

from scaldys.common.app_logging import setup_logging

# https://github.com/mCodingLLC/VideosSampleCode/tree/master/videos/135_modern_logging
# use <application_name> in all files for the logger
# __name__ is another common choice, but would create multiple equivalent instances in memory
logger = logging.getLogger("scaldys")


__all__ = ["hello"]


def hello(n: int) -> str:
    """Greet the sum from 0 to n (exclusive end)."""
    sum_n = sum(range(n))
    return f"Hello {sum_n}!"


def main():
    setup_logging()
    logging.basicConfig(level="INFO")
    logger.debug("debug message", extra={"x": "hello"})
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("exception message")


if __name__ == "__main__":
    main()
