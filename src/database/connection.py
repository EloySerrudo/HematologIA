"""SQLite connection management.

Provides a context manager that:
  * Connects to the configured database file.
  * Enables foreign key constraints (off by default in SQLite).
  * Returns rows as ``sqlite3.Row`` so they can be accessed by column name.
  * Commits on successful exit, rolls back on exception, always closes.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from src.config import DB_PATH
from src.core.logger import get_logger

_logger = get_logger(__name__)


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    """Yield a configured SQLite connection.

    Args:
        db_path: Override path to the database file. Defaults to
            ``src.config.DB_PATH``.

    Yields:
        A SQLite connection with row factory set and FK enforcement enabled.

    Raises:
        Re-raises any exception from the wrapped block after rolling back.
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(
        str(path),
        detect_types=sqlite3.PARSE_DECLTYPES,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        # We log the error type/message but not the full SQL or params, since
        # those could contain sensitive data (e.g. password hashes).
        _logger.error("Database operation failed: %s: %s", type(exc).__name__, exc)
        raise
    finally:
        conn.close()
