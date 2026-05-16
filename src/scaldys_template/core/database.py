# -*- coding: utf-8 -*-
# cython: language_level=3

"""
Database abstraction layer — template / reference implementation.

This module provides scaffold code for database access.  None of the methods
connect to a real database; they log the operation they *would* perform and
return plausible stub data.  Replace the stub bodies with your actual driver
calls (psycopg, asyncpg, sqlite3, SQLAlchemy, etc.) while keeping the same
public interface.

Key patterns demonstrated
--------------------------
- Dataclass for typed, validated connection configuration (DatabaseConfig)
- Context-manager connection lifecycle: __enter__ / __exit__ guarantee that
  disconnect() is called even when an exception is raised inside the `with`
  block
- Parameterised query execution stub — signature matches typical DB-API 2.0
  drivers so the real implementation is a drop-in replacement
- @contextmanager transaction helper that wraps begin/commit/rollback around
  a block of execute() calls
- ConnectionPool stub showing the acquire/release pattern backed by a
  threading.Semaphore so the pool is thread-safe; real pools (e.g. psycopg
  pool, SQLAlchemy pool) follow the same interface

Usage examples (in a CLI command)
-----------------------------------
    # Simple connection:
    config = DatabaseConfig(host="localhost", name="mydb", user="admin")
    with DatabaseConnection(config) as conn:
        rows = conn.execute("SELECT * FROM items WHERE id = %s", (item_id,))

    # Transactional block:
    with DatabaseConnection(config) as conn:
        with transaction(conn):
            conn.execute("INSERT INTO log (msg) VALUES (%s)", ("started",))
            conn.execute("UPDATE items SET processed = TRUE WHERE id = %s", (item_id,))

    # Pool (long-running service):
    pool = ConnectionPool(config, max_connections=10)
    with pool.acquire() as conn:
        rows = conn.execute("SELECT count(*) FROM items")
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator

from scaldys_template.__about__ import PACKAGE_NAME

__all__ = ["DatabaseConfig", "DatabaseConnection", "ConnectionPool", "transaction"]

logger = logging.getLogger(PACKAGE_NAME)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class DatabaseConfig:
    """
    Immutable configuration for a single database connection.

    In a real project, populate this from environment variables, a secrets
    manager, or AppSettings.  Never hard-code credentials.

    Attributes
    ----------
    host : str
        Hostname or IP address of the database server.
    port : int
        TCP port.  Defaults to 5432 (PostgreSQL convention).
    name : str
        Database / schema name to connect to.
    user : str
        Authentication username.
    password : str
        Authentication password.  In production, load from an env var or vault.
    connect_timeout : float
        Seconds to wait for the initial connection before raising.
    """

    host: str = "localhost"
    port: int = 5432
    name: str = "appdb"
    user: str = "appuser"
    password: str = field(default="", repr=False)  # repr=False hides password in logs
    connect_timeout: float = 5.0


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class DatabaseConnection:
    """
    A single database connection with context-manager support.

    Typical usage::

        with DatabaseConnection(config) as conn:
            rows = conn.execute("SELECT * FROM items", ())

    The connection is opened in __enter__ and closed in __exit__.  If an
    exception propagates out of the `with` block, __exit__ still calls
    disconnect() so no connection is leaked.
    """

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._connected = False
        self._row_count: int = 0
        # In a real driver this would be the underlying connection object,
        # e.g. a psycopg.Connection or sqlite3.Connection.
        self._raw_conn: object | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Open the database connection.

        Stub: logs the connection attempt and sets the internal flag.
        Replace with your driver's connect() / create_engine() call.
        """
        logger.debug(
            "Connecting to database",
            extra={
                "host": self._config.host,
                "port": self._config.port,
                "db": self._config.name,
                "user": self._config.user,
            },
        )
        # --- replace with real driver call, e.g.: ---
        # import psycopg
        # self._raw_conn = psycopg.connect(
        #     host=self._config.host, port=self._config.port,
        #     dbname=self._config.name, user=self._config.user,
        #     password=self._config.password, connect_timeout=self._config.connect_timeout,
        # )
        self._connected = True
        logger.info("Database connection established", extra={"db": self._config.name})

    def disconnect(self) -> None:
        """
        Close the database connection.

        Stub: logs the disconnection.  Replace with your driver's close() call.
        Safe to call even if not connected (no-op).
        """
        if not self._connected:
            return
        logger.debug("Disconnecting from database", extra={"db": self._config.name})
        # self._raw_conn.close()
        self._raw_conn = None
        self._connected = False

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> DatabaseConnection:
        self.connect()
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> bool:
        self.disconnect()
        return False  # do not suppress exceptions

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    def execute(self, query: str, params: tuple = ()) -> list[dict]:
        """
        Execute a parameterised SQL query and return the result rows.

        Parameters
        ----------
        query : str
            SQL statement.  Use %s (DB-API 2.0) or ? (sqlite3) placeholders.
        params : tuple
            Positional parameters bound to the query placeholders.

        Returns
        -------
        list[dict]
            Each dict maps column name → value.  Empty list for statements
            that produce no rows (INSERT, UPDATE, DELETE).

        Stub behaviour: logs the query, updates row_count, returns fake rows.
        In production, replace with self._raw_conn.cursor().execute(query, params).
        """
        if not self._connected:
            raise RuntimeError("Cannot execute query: not connected to database")

        logger.debug(
            "Executing query",
            extra={"query": query[:120], "param_count": len(params)},
        )

        # --- replace with real driver call, e.g.: ---
        # with self._raw_conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        #     cur.execute(query, params)
        #     rows = cur.fetchall() or []
        #     self._row_count = cur.rowcount
        # return rows

        # Stub: return a small set of fake rows so callers have something to
        # work with without a real database.
        stub_rows = [
            {"id": 1, "name": "stub_row_1", "value": 42},
            {"id": 2, "name": "stub_row_2", "value": 99},
        ]
        self._row_count = len(stub_rows)
        return stub_rows

    @property
    def row_count(self) -> int:
        """Number of rows affected or returned by the last execute() call."""
        return self._row_count


# ---------------------------------------------------------------------------
# Transaction helper
# ---------------------------------------------------------------------------


@contextmanager
def transaction(conn: DatabaseConnection) -> Generator[DatabaseConnection, None, None]:
    """
    Context manager that wraps a block of execute() calls in a transaction.

    Commits on clean exit; rolls back if an exception propagates.

    Usage::

        with DatabaseConnection(config) as conn:
            with transaction(conn):
                conn.execute("INSERT INTO events (msg) VALUES (%s)", ("start",))
                conn.execute("UPDATE counters SET n = n + 1 WHERE name = %s", ("runs",))

    Stub: logs BEGIN / COMMIT / ROLLBACK instead of issuing real SQL.
    Replace the stub comments with driver-specific transaction calls.
    """
    logger.debug("BEGIN transaction")
    # conn._raw_conn.autocommit = False  # e.g. for psycopg

    try:
        yield conn
        logger.debug("COMMIT transaction")
        # conn._raw_conn.commit()
    except Exception:
        logger.warning("ROLLBACK transaction — exception in transaction block", exc_info=True)
        # conn._raw_conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------


class ConnectionPool:
    """
    Thread-safe connection pool with a configurable maximum size.

    Limits the number of simultaneously open connections using a
    threading.Semaphore.  Each thread acquires the semaphore before opening a
    connection and releases it when done.

    Usage::

        pool = ConnectionPool(config, max_connections=10)

        # Use as a context manager:
        with pool.acquire() as conn:
            rows = conn.execute("SELECT 1")

        # Or manually:
        conn = pool.checkout()
        try:
            rows = conn.execute("SELECT 1")
        finally:
            pool.checkin(conn)

    In production, replace this class with a real pooling library such as:
      - psycopg_pool.ConnectionPool  (PostgreSQL)
      - sqlalchemy.pool.QueuePool    (any SQLAlchemy dialect)
      - aiopg / asyncpg pool         (async PostgreSQL)
    """

    def __init__(self, config: DatabaseConfig, max_connections: int = 5) -> None:
        self._config = config
        self._max_connections = max_connections
        self._semaphore = threading.Semaphore(max_connections)
        logger.debug(
            "Connection pool initialised",
            extra={"max_connections": max_connections, "db": config.name},
        )

    def checkout(self) -> DatabaseConnection:
        """
        Acquire a connection from the pool (blocks if pool is exhausted).

        The caller is responsible for calling checkin() when done.
        Prefer using acquire() as a context manager instead.
        """
        self._semaphore.acquire()
        conn = DatabaseConnection(self._config)
        conn.connect()
        return conn

    def checkin(self, conn: DatabaseConnection) -> None:
        """Return a connection to the pool."""
        conn.disconnect()
        self._semaphore.release()

    @contextmanager
    def acquire(self) -> Generator[DatabaseConnection, None, None]:
        """
        Context manager: check out a connection, yield it, then check it in.

        Usage::

            with pool.acquire() as conn:
                rows = conn.execute("SELECT 1")
        """
        conn = self.checkout()
        try:
            yield conn
        finally:
            self.checkin(conn)
