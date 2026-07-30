"""
SQLite connection manager.

Uses WAL (Write-Ahead Logging) journal mode so background threads can write
while the UI thread reads without locking conflicts.

Thread safety: Each thread should call get_connection() to obtain its own
connection. SQLite connections must not be shared across threads.
"""

import sqlite3
import threading
from app.utils.constants import DB_PATH


_local = threading.local()
_db_path_override: str | None = None


def set_db_path(db_path: str | None) -> None:
    """Override database file path (used during unit testing to isolate test DB)."""
    global _db_path_override
    _db_path_override = db_path
    close_connection()


def get_connection() -> sqlite3.Connection:
    """
    Return a per-thread SQLite connection.
    Creates the connection on first access for each thread.
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        target_path = _db_path_override or DB_PATH
        conn = sqlite3.connect(target_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        if target_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _local.conn = conn
    return conn


def close_connection() -> None:
    """Close the per-thread connection if open."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None
