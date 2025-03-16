# -*- coding: utf-8 -*-
# cython: language_level=3

import atexit
import datetime as dt
import json
import logging
import pathlib

from logging.config import dictConfig
from logging.handlers import QueueHandler
from typing import override

from scaldys.__about__ import PACKAGE_NAME
from scaldys.common.app_location import AppLocation

__all__ = ["setup_logging"]


LOG_FILE_NAME = f"{PACKAGE_NAME}.log"

# Largely inspired from :
# https://github.com/mCodingLLC/VideosSampleCode/tree/master/videos/135_modern_logging
# logging configuration not read from a configuration file, but directly embedded here.


def setup_logging(level: str | None = "info", verbose: bool = False) -> None:
    """
    Configure and initialize logging for the application.

    This function sets up the logging system with both file and console handlers.
    Log files are stored in JSON Lines format in the application's log directory.
    The logging level can be configured, and console output can be controlled
    via the verbose parameter.

    Parameters
    ----------
    level : str or None, default="info"
        The logging level to set. Valid values are: "off", "debug", "info", "warning", "error", "critical".
        If "off" is specified, logging is disabled. If None is provided, it defaults to "info".
    verbose : bool, default=False
        If True, log messages are output to console according to the specified level.
        If False, console output is limited to CRITICAL level messages and above.

    Raises
    ------
    AssertionError
        If an invalid log level is provided.
    Exception
        If there are issues creating log directories or configuring handlers.

    """

    if level is None:
        level = "info"

    assert level.lower() in ["off", "debug", "info", "warning", "error", "critical"], (
        f"Invalid log level ({level})."
    )

    log_path = AppLocation.get_directory(AppLocation.LogDir)
    if not log_path.exists():
        log_path.mkdir(parents=True)

    log_file_path = log_path.joinpath(LOG_FILE_NAME + ".jsonl")

    _configure_logging(log_file_path)

    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        # Lines 1 and 3 below are needed for type consistency checking by PyRight
        assert isinstance(queue_handler, QueueHandler)
        queue_listener = queue_handler.listener
        # listener added in Python 3.12; can be None for older versions
        assert queue_listener is not None
        queue_listener.start()
        atexit.register(queue_listener.stop)

    logger = logging.getLogger(PACKAGE_NAME)
    # getattr() transforms log_level string to the corresponding integer value
    if level == "off":
        if verbose:
            numeric_level = getattr(logging, "INFO")
        else:
            # turn off the logging messages to standard output by specifying a log level above critical
            numeric_level = getattr(logging, "CRITICAL") + 1
    else:
        numeric_level = getattr(logging, level.upper())

    logger.setLevel(numeric_level)

    # if verbose, use the log level given by the function parameter,
    if not verbose:
        stdout_handler = logging.getHandlerByName("stdout")
        if stdout_handler is not None:
            stdout_handler.setLevel(logging.CRITICAL + 1)


def _configure_logging(log_file_path: pathlib.Path) -> None:
    # Only the json formatter and the queue_handler are used, leave the others as example
    # QueueHandler: only the file_json handler is used.
    # For user info/progress on the command line, use the verbose flag when invoking this CLI app.
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "verbose_true": {
                    "()": f"{PACKAGE_NAME}.common.app_logging.NonErrorFilter",
                }
            },
            "formatters": {
                "verbose": {
                    "format": "%(asctime)s %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
                "console": {
                    "format": "%(asctime)s [%(levelname)-s|L%(lineno)-d|%(module)-s] %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
                "json": {
                    "()": f"{PACKAGE_NAME}.common.app_logging.JsonFormatter",
                    "fmt_keys": {
                        "level": "levelname",
                        "message": "message",
                        "timestamp": "timestamp",
                        "logger": "name",
                        "module": "module",
                        "function": "funcName",
                        "line": "lineno",
                        "thread_name": "threadName",
                    },
                },
            },
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "console",
                    "stream": "ext://sys.stderr",
                },
                "stdout": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "verbose",
                    "stream": "ext://sys.stdout",
                },
                "file_json": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "json",
                    "filename": log_file_path,
                    "maxBytes": 10000,
                    "backupCount": 3,
                },
                "queue_handler": {
                    "class": "logging.handlers.QueueHandler",
                    "handlers": ["file_json"],
                    "respect_handler_level": True,
                },
            },
            "loggers": {
                "root": {"level": "INFO", "handlers": ["stderr"], "propagate": True},
                f"{PACKAGE_NAME}": {
                    "level": "DEBUG",
                    "handlers": ["queue_handler", "stdout"],
                    "propagate": False,
                },
            },
        }
    )


# Custom Logger producing logs in JSON format

LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def __init__(
        self,
        *,
        fmt_keys: dict[str, str] | None = None,
    ):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    @override
    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord) -> dict[str, str | None]:
        always_fields = {
            "message": record.getMessage(),
            "timestamp": dt.datetime.fromtimestamp(record.created, tz=dt.timezone.utc).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: msg_val
            if (msg_val := always_fields.pop(val, None)) is not None
            else getattr(record, val)
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)

        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                message[key] = val

        return message


class NonErrorFilter(logging.Filter):
    """
    A logging filter to exclude log records containing error-level messages.
    """

    @override
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return record.levelno <= logging.INFO
