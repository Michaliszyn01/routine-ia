from __future__ import annotations

import sqlite3
from collections.abc import Callable


Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]


def run_migrations(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        int(row["version"])
        for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
    }
    for version, name, migration in MIGRATIONS:
        if version in applied:
            continue
        migration(connection)
        connection.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (version, name),
        )
        connection.execute(f"PRAGMA user_version = {version}")


def _migration_001_unified_work(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            area TEXT NOT NULL DEFAULT 'rotina',
            status TEXT NOT NULL DEFAULT 'pending',
            priority INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 4),
            due_date TEXT,
            scheduled_for TEXT,
            estimated_minutes INTEGER NOT NULL DEFAULT 25 CHECK (estimated_minutes BETWEEN 1 AND 1440),
            subject TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'manual',
            project_id INTEGER,
            parent_task_id INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status_due
            ON tasks(status, due_date, scheduled_for);
        CREATE INDEX IF NOT EXISTS idx_tasks_area_status
            ON tasks(area, status);
        CREATE INDEX IF NOT EXISTS idx_tasks_project
            ON tasks(project_id);

        CREATE TABLE IF NOT EXISTS study_review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_error_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            next_review_date TEXT NOT NULL,
            interval_days INTEGER NOT NULL DEFAULT 1,
            repetitions INTEGER NOT NULL DEFAULT 0,
            ease_factor REAL NOT NULL DEFAULT 2.5,
            last_quality INTEGER,
            last_reviewed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (study_error_id) REFERENCES study_errors(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_study_review_due
            ON study_review_queue(status, next_review_date);
        """
    )


MIGRATIONS: tuple[Migration, ...] = (
    (1, "unified_tasks_and_study_reviews", _migration_001_unified_work),
)
