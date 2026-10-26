from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .database import BACKUPS_DIR, DB_PATH, get_connection


def get_backup_dir() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUPS_DIR


def create_backup(reason: str = "manual") -> dict:
    get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUPS_DIR / f"routine_backup_{timestamp}.db"

    status = "success"
    message = f"Backup criado com sucesso ({reason}). Banco local completo, incluindo Uso do PC."

    try:
        with sqlite3.connect(DB_PATH) as source:
            with sqlite3.connect(backup_path) as target:
                source.backup(target)
    except Exception as exc:
        status = "error"
        message = str(exc)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO backups_log (backup_path, status, message)
            VALUES (?, ?, ?)
            """,
            (str(backup_path), status, message),
        )

    if status != "success":
        raise RuntimeError(message)

    enforce_backup_retention()
    return {
        "backup_path": str(backup_path),
        "filename": backup_path.name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "message": message,
    }


def list_backups(limit: int = 20) -> list[dict]:
    get_backup_dir()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, backup_path, created_at, status, message
            FROM backups_log
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    backups = []
    for row in rows:
        path = Path(row["backup_path"])
        backups.append(
            {
                "id": row["id"],
                "backup_path": row["backup_path"],
                "filename": path.name,
                "exists": path.exists(),
                "size": path.stat().st_size if path.exists() else 0,
                "created_at": row["created_at"],
                "status": row["status"],
                "message": row["message"],
            }
        )
    return backups


def get_auto_backup_settings() -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM auto_backup_settings WHERE id = 1").fetchone()
    if not row:
        return {"enabled": 1, "frequency": "daily", "keep_last": 10, "last_backup_at": None}
    return dict(row)


def update_auto_backup_settings(payload: dict) -> dict:
    enabled = 1 if payload.get("enabled", True) else 0
    frequency = str(payload.get("frequency") or "daily").strip().lower()
    if frequency not in {"daily", "weekly"}:
        frequency = "daily"
    try:
        keep_last = max(1, min(int(payload.get("keep_last") or 10), 100))
    except (TypeError, ValueError):
        keep_last = 10

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO auto_backup_settings (id, enabled, frequency, keep_last, updated_at)
            VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                enabled = excluded.enabled,
                frequency = excluded.frequency,
                keep_last = excluded.keep_last,
                updated_at = CURRENT_TIMESTAMP
            """,
            (enabled, frequency, keep_last),
        )
    enforce_backup_retention()
    return get_auto_backup_settings()


def maybe_create_auto_backup(reason: str = "startup") -> dict | None:
    settings = get_auto_backup_settings()
    if not int(settings.get("enabled") or 0):
        return None

    last_backup_at = settings.get("last_backup_at")
    threshold_hours = 24 if settings.get("frequency") == "daily" else 24 * 7
    should_backup = True
    if last_backup_at:
        try:
            last = datetime.fromisoformat(str(last_backup_at).replace(" ", "T"))
            should_backup = datetime.now() - last >= timedelta(hours=threshold_hours)
        except ValueError:
            should_backup = True

    if not should_backup:
        return None

    backup = create_backup(reason=reason)
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE auto_backup_settings
            SET last_backup_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """
        )
    return backup


def enforce_backup_retention() -> None:
    settings = get_auto_backup_settings()
    keep_last = int(settings.get("keep_last") or 10)
    backups = list_backups(limit=500)
    successful = [backup for backup in backups if backup["status"] == "success"]
    for backup in successful[keep_last:]:
        path = Path(backup["backup_path"])
        try:
            if path.exists() and path.resolve() != DB_PATH.resolve():
                path.unlink()
        except OSError:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO backups_log (backup_path, status, message)
                    VALUES (?, 'error', ?)
                    """,
                    (str(path), "Falha ao aplicar retencao de backups."),
                )
