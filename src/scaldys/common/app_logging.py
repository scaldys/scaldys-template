# -*- coding: utf-8 -*-
# cython: language_level=3

import atexit
import datetime as dt
import json
import logging
import pathlib

from logging.config import dictConfig
from typing import override

from scaldys.common.app_location import AppLocation

__all__ = ["setup_logging"]


LOG_FILE_NAME = "scaldys.log"

# Largely inspired from :
# https://github.com/mCodingLLC/VideosSampleCode/tree/master/videos/135_modern_logging
# logging configuration not read from a configuration file, but directly embedded here.


def setup_logging() -> None:
    """Configure the logging for the application.
    """
    log_path = AppLocation.get_directory(AppLocation.LogDir)
    if not log_path.exists():
        log_path.mkdir(parents=True)

    log_file_path = log_path.joinpath(LOG_FILE_NAME + ".jsonl")

    _configure_logging(log_file_path)

    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


def _configure_logging(log_file_path: pathlib.Path) -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "format": "%(asctime)s [%(levelname)-8s|%(module)s|L%(lineno)d] %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z"
                },
                "json": {
                    "()": "common.app_logging.MyJSONFormatter",
                    "fmt_keys": {
                        "level": "levelname",
                        "message": "message",
                        "timestamp": "timestamp",
                        "logger": "name",
                        "module": "module",
                        "function": "funcName",
                        "line": "lineno",
                        "thread_name": "threadName"
                    }
                }
            },
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "level": "WARNING",
                    "formatter": "console",
                    "stream": "ext://sys.stderr"
                },
                "file_json": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "json",
                    "filename": log_file_path,
                    "maxBytes": 10000,
                    "backupCount": 3
                },
                "queue_handler": {
                    "class": "logging.handlers.QueueHandler",
                    "handlers": [
                        "stderr",
                        "file_json"
                    ],
                    "respect_handler_level": True
                }
            },
            "loggers": {
                "root": {
                    "level": "DEBUG",
                    "handlers": [
                        "queue_handler"
                    ]
                }
            }
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


class MyJSONFormatter(logging.Formatter):
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
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc
            ).isoformat(),
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
