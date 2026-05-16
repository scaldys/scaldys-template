# -*- coding: utf-8 -*-

"""
Unit tests for scaldys.core.database.

Patterns demonstrated
----------------------
- Testing context manager __enter__ / __exit__ lifecycle.
- Asserting state changes (connected flag) rather than real I/O.
- caplog to verify that expected log messages are emitted.
- pytest.raises inside a with-block to verify the exception propagates.
- Testing the transaction() @contextmanager helper.
- Testing ConnectionPool semaphore logic via thread counting.
"""

from __future__ import annotations

import logging
import threading

import pytest

from scaldys_template.core.database import (
    ConnectionPool,
    DatabaseConfig,
    DatabaseConnection,
    transaction,
)


@pytest.fixture
def config() -> DatabaseConfig:
    return DatabaseConfig(host="testhost", port=5432, name="testdb", user="testuser")


@pytest.fixture
def conn(config: DatabaseConfig) -> DatabaseConnection:
    return DatabaseConnection(config)


# ---------------------------------------------------------------------------
# DatabaseConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDatabaseConfig:
    def test_default_host_is_localhost(self):
        cfg = DatabaseConfig()
        assert cfg.host == "localhost"

    def test_default_port_is_5432(self):
        cfg = DatabaseConfig()
        assert cfg.port == 5432

    def test_password_hidden_in_repr(self):
        cfg = DatabaseConfig(password="s3cr3t")
        assert "s3cr3t" not in repr(cfg)


# ---------------------------------------------------------------------------
# DatabaseConnection — lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDatabaseConnectionLifecycle:
    def test_not_connected_on_construction(self, conn: DatabaseConnection):
        assert conn._connected is False

    def test_connected_after_connect(self, conn: DatabaseConnection):
        conn.connect()
        assert conn._connected is True
        conn.disconnect()

    def test_disconnected_after_disconnect(self, conn: DatabaseConnection):
        conn.connect()
        conn.disconnect()
        assert conn._connected is False

    def test_disconnect_when_not_connected_is_noop(self, conn: DatabaseConnection):
        """Calling disconnect on an already-disconnected connection must not raise."""
        conn.disconnect()  # should be silent

    def test_connect_logs_connection(
        self, conn: DatabaseConnection, caplog: pytest.LogCaptureFixture
    ):
        with caplog.at_level(logging.INFO, logger="scaldys_template"):
            conn.connect()
        conn.disconnect()
        assert any("connection established" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# DatabaseConnection — context manager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDatabaseConnectionContextManager:
    def test_enter_sets_connected(self, config: DatabaseConfig):
        with DatabaseConnection(config) as c:
            assert c._connected is True

    def test_exit_sets_disconnected(self, config: DatabaseConfig):
        with DatabaseConnection(config) as c:
            pass
        assert c._connected is False

    def test_exit_called_on_exception(self, config: DatabaseConfig):
        """__exit__ must run (and disconnect) even when an exception is raised."""
        conn_ref: list[DatabaseConnection] = []
        with pytest.raises(ValueError):
            with DatabaseConnection(config) as c:
                conn_ref.append(c)
                raise ValueError("body error")
        assert conn_ref[0]._connected is False


# ---------------------------------------------------------------------------
# DatabaseConnection — execute
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDatabaseConnectionExecute:
    def test_execute_raises_when_not_connected(self, conn: DatabaseConnection):
        with pytest.raises(RuntimeError, match="not connected"):
            conn.execute("SELECT 1")

    def test_execute_returns_list(self, config: DatabaseConfig):
        with DatabaseConnection(config) as c:
            rows = c.execute("SELECT * FROM stub")
            assert isinstance(rows, list)

    def test_execute_returns_dicts(self, config: DatabaseConfig):
        with DatabaseConnection(config) as c:
            rows = c.execute("SELECT * FROM stub")
            assert all(isinstance(row, dict) for row in rows)

    def test_row_count_updated_after_execute(self, config: DatabaseConfig):
        with DatabaseConnection(config) as c:
            rows = c.execute("SELECT * FROM stub")
            assert c.row_count == len(rows)


# ---------------------------------------------------------------------------
# transaction helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTransaction:
    def test_normal_flow_logs_commit(
        self, config: DatabaseConfig, caplog: pytest.LogCaptureFixture
    ):
        with caplog.at_level(logging.DEBUG, logger="scaldys_template"):
            with DatabaseConnection(config) as c:
                with transaction(c):
                    c.execute("SELECT 1")
        messages = [r.message.upper() for r in caplog.records]
        assert any("COMMIT" in m for m in messages)

    def test_exception_logs_rollback(
        self, config: DatabaseConfig, caplog: pytest.LogCaptureFixture
    ):
        with caplog.at_level(logging.WARNING, logger="scaldys_template"):
            with pytest.raises(RuntimeError):
                with DatabaseConnection(config) as c:
                    with transaction(c):
                        raise RuntimeError("force rollback")
        messages = [r.message.upper() for r in caplog.records]
        assert any("ROLLBACK" in m for m in messages)

    def test_exception_is_reraised(self, config: DatabaseConfig):
        """The transaction context manager must NOT swallow exceptions."""
        with pytest.raises(ValueError, match="should propagate"):
            with DatabaseConnection(config) as c:
                with transaction(c):
                    raise ValueError("should propagate")


# ---------------------------------------------------------------------------
# ConnectionPool
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConnectionPool:
    def test_acquire_yields_connected_connection(self, config: DatabaseConfig):
        pool = ConnectionPool(config, max_connections=3)
        with pool.acquire() as c:
            assert c._connected is True

    def test_acquire_releases_on_exit(self, config: DatabaseConfig):
        pool = ConnectionPool(config, max_connections=2)
        with pool.acquire() as c:
            pass
        # After context exit the semaphore should be at its original value
        # (we can verify by acquiring again without blocking).
        acquired = pool._semaphore.acquire(blocking=False)
        assert acquired is True
        pool._semaphore.release()  # restore

    def test_pool_limits_concurrent_connections(self, config: DatabaseConfig):
        """
        With max_connections=1, a second concurrent acquire must block until
        the first is released.  We verify this with threading.

        Pattern: start a thread that holds the only connection for 0.1 s.
        The main thread tries to acquire with a short timeout.  It should
        fail to acquire during that window, succeed after the thread releases.
        """
        import time

        pool = ConnectionPool(config, max_connections=1)

        results: list[str] = []

        def _hold_connection():
            with pool.acquire():
                time.sleep(0.05)
                results.append("released")

        t = threading.Thread(target=_hold_connection)
        t.start()

        # Give the thread a moment to acquire.
        time.sleep(0.01)

        # Try to acquire from main thread — semaphore is at 0, so this should
        # block until the thread releases.
        with pool.acquire():
            results.append("main acquired")

        t.join()

        assert results == ["released", "main acquired"], (
            "Main thread should not have acquired before the worker released"
        )
