# -*- coding: utf-8 -*-

import logging
from scaldys.__about__ import PACKAGE_NAME

from scaldys.common.logging import setup_logging
from scaldys.cli.cli import app


# https://github.com/mCodingLLC/VideosSampleCode/tree/master/videos/135_modern_logging
# use <application_name> in all files for the logger
# __name__ is another common choice, but would create multiple equivalent instances in memory
logger = logging.getLogger(PACKAGE_NAME)


def main():
    setup_logging(level="debug", verbose=True)
    logging.basicConfig(level="INFO")
    logger.debug("debug message", extra={"x": "hello"})
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")

    app()


if __name__ == "__main__":
    main()
