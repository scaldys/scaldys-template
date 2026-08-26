"""
Unit tests for scaldys.common.logging.

Patterns demonstrated
----------------------
- Testing logging infrastructure without writing to real directories
  (isolated_app_location fixture)
- caplog fixture for capturing log records in tests
- Direct instantiation of Formatter / Filter classes for focused unit tests
- Parametrize over all valid log levels
"""

from __future__ import annotations

import json
import logging

import pytest

from scaldys_template.__about__ import PACKAGE_NAME
from scaldys_template.common.logging import (
    JsonFormatter,
    NonErrorFilter,
    setup_logging,
)

# ---------------------------------------------------------------------------
# NonErrorFilter
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNonErrorFilter:
    """NonErrorFilter should pass DEBUG and INFO but block WARNING and above."""

    @pytest.fixture
    def filter_(self) -> NonErrorFilter:
        return NonErrorFilter()

    def _make_record(self, level: int) -> logging.LogRecord:
        return logging.LogRecord(
            name="test",
            level=level,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

    @pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
    def test_passes_debug_and_info(self, filter_: NonErrorFilter, level: int):
        record = self._make_record(level)
        assert filter_.filter(record) is True

    @pytest.mark.parametrize("level", [logging.WARNING, logging.ERROR, logging.CRITICAL])
    def test_blocks_warning_and_above(self, filter_: NonErrorFilter, level: int):
        record = self._make_record(level)
        assert filter_.filter(record) is False


# ---------------------------------------------------------------------------
# JsonFormatter
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJsonFormatter:
    """JsonFormatter should produce valid, well-structured JSON lines."""

    @pytest.fixture
    def formatter(self) -> JsonFormatter:
        return JsonFormatter(
            fmt_keys={
                "level": "levelname",
                "message": "message",
                "logger": "name",
                "line": "lineno",
            }
        )

    def _make_record(self, msg: str = "hello", level: int = logging.INFO) -> logging.LogRecord:
        record = logging.LogRecord(
            name=PACKAGE_NAME,
            level=level,
            pathname=__file__,
            lineno=42,
            msg=msg,
            args=(),
            exc_info=None,
        )
        return record

    def test_output_is_valid_json(self, formatter: JsonFormatter):
        output = formatter.format(self._make_record())
        parsed = json.loads(output)  # raises if invalid JSON
        assert isinstance(parsed, dict)

    def test_contains_mapped_keys(self, formatter: JsonFormatter):
        output = json.loads(formatter.format(self._make_record()))
        assert "level" in output
        assert "message" in output
        assert "logger" in output

    def test_message_content_is_correct(self, formatter: JsonFormatter):
        output = json.loads(formatter.format(self._make_record("my message")))
        assert output["message"] == "my message"

    def test_timestamp_field_is_present(self, formatter: JsonFormatter):
        # timestamp is always added, regardless of fmt_keys
        output = json.loads(formatter.format(self._make_record()))
        assert "timestamp" in output

    def test_extra_fields_are_included(self, formatter: JsonFormatter):
        """Extra fields passed to logger.info(..., extra={...}) appear in JSON."""
        record = self._make_record()
        record.request_id = "abc-123"  # simulate an extra field
        output = json.loads(formatter.format(record))
        assert output.get("request_id") == "abc-123"


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSetupLogging:
    """Tests for the setup_logging() public function."""

    def test_invalid_level_raises_value_error(self, isolated_app_location):
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging("verbose")  # not a valid level name

    def test_none_level_defaults_to_info(self, isolated_app_location):
        # Should not raise; None is treated as "info".
        setup_logging(None)
        logger = logging.getLogger(PACKAGE_NAME)
        assert logger.level == logging.INFO

    @pytest.mark.parametrize(
        "level_str, expected_int",
        [
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ],
    )
    def test_valid_levels_set_logger_level(
        self, isolated_app_location, level_str: str, expected_int: int
    ):
        setup_logging(level_str)
        logger = logging.getLogger(PACKAGE_NAME)
        assert logger.level == expected_int

    def test_off_level_sets_above_critical(self, isolated_app_location):
        setup_logging("off")
        logger = logging.getLogger(PACKAGE_NAME)
        assert logger.level > logging.CRITICAL

    def test_creates_log_file(self, isolated_app_location):
        setup_logging("info")
        log_dir = isolated_app_location[3]  # AppLocation.LogDir == 3
        jsonl_files = list(log_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1, "Expected exactly one .jsonl log file"

    def test_case_insensitive_level(self, isolated_app_location):
        """Level string matching should be case-insensitive."""
        setup_logging("INFO")  # uppercase
        setup_logging("Debug")  # mixed case
        # No exception → test passes
