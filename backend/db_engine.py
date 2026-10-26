from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .paths import get_database_path


DEFAULT_TIMEOUT_SECONDS = 10
BUSY_TIMEOUT_MS = 5_000


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Create the single configured SQLite connection used by the application."""
    database_path = Path(path) if path is not None else get_database_path()
    connection = sqlite3.connect(database_path, timeout=DEFAULT_TIMEOUT_SECONDS)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


@contextmanager
def transaction(*, immediate: bool = False) -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def diagnostics() -> dict:
    database_path = get_database_path()
    with connect(database_path) as connection:
        integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        version_row = connection.execute("PRAGMA user_version").fetchone()
        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    return {
        "path": str(database_path),
        "size_bytes": database_path.stat().st_size if database_path.exists() else 0,
        "integrity": integrity,
        "journal_mode": journal_mode,
        "foreign_keys": bool(foreign_keys),
        "schema_version": int(version_row[0] if version_row else 0),
        "table_count": int(table_count),
    }
