from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.database import get_connection


def ensure_health_importer_schema() -> None:
    with get_connection() as conn:
        conn.executescript(HEALTH_IMPORTER_SCHEMA)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def has_successful_import(file_hash: str, data_type: str) -> bool:
    ensure_health_importer_schema()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id FROM health_imported_files
            WHERE file_hash = ? AND data_type = ? AND status = 'success'
            LIMIT 1
            """,
            (file_hash, data_type),
        ).fetchone()
    return row is not None


def record_imported_file(
    *,
    file_path: str,
    file_hash: str,
    data_type: str,
    rows_imported: int,
    status: str,
    error_message: str = "",
) -> None:
    ensure_health_importer_schema()
    path = Path(file_path)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO health_imported_files (
                file_path, file_name, file_hash, data_type, imported_at,
                rows_imported, status, error_message
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
            ON CONFLICT(file_hash, data_type) DO UPDATE SET
                file_path = excluded.file_path,
                file_name = excluded.file_name,
                imported_at = CURRENT_TIMESTAMP,
                rows_imported = excluded.rows_imported,
                status = excluded.status,
                error_message = excluded.error_message
            """,
            (str(path), path.name, file_hash, data_type, rows_imported, status, error_message[:1000]),
        )


def save_sleep_records(records: list) -> tuple[int, set[str]]:
    ensure_health_importer_schema()
    inserted = 0
    dates = {record.date for record in records}
    with get_connection() as conn:
        for record in records:
            payload = asdict(record)
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO health_import_records (
                    record_key, data_type, date, payload_json, source_file
                )
                VALUES (?, 'sleep', ?, ?, ?)
                """,
                (_sleep_key(record), record.date, json.dumps(payload, ensure_ascii=False), record.source_file),
            )
            inserted += cursor.rowcount
        for date_value in dates:
            _rebuild_sleep_summary(conn, date_value)
    return inserted, dates


def save_steps_records(records: list) -> tuple[int, set[str]]:
    ensure_health_importer_schema()
    inserted = 0
    dates = {record.date for record in records}
    with get_connection() as conn:
        for record in records:
            payload = asdict(record)
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO health_import_records (
                    record_key, data_type, date, payload_json, source_file
                )
                VALUES (?, 'steps', ?, ?, ?)
                """,
                (_steps_key(record), record.date, json.dumps(payload, ensure_ascii=False), record.source_file),
            )
            inserted += cursor.rowcount
        for date_value in dates:
            _rebuild_steps_summary(conn, date_value)
    return inserted, dates


def save_activity_records(records: list) -> tuple[int, set[str]]:
    ensure_health_importer_schema()
    inserted = 0
    dates = {record.date for record in records}
    with get_connection() as conn:
        for record in records:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO health_activities (
                    date, start_time, activity_type, activity_name, elapsed_seconds,
                    active_seconds, distance_km, source_file
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.date,
                    record.start_time,
                    record.activity_type,
                    record.activity_name,
                    record.elapsed_seconds,
                    record.active_seconds,
                    record.distance_km,
                    record.source_file,
                ),
            )
            inserted += cursor.rowcount
    return inserted, dates


def save_heart_rate_summaries(summaries: list) -> tuple[int, set[str]]:
    ensure_health_importer_schema()
    affected = {summary.date for summary in summaries}
    with get_connection() as conn:
        for summary in summaries:
            conn.execute(
                """
                INSERT INTO health_heart_rate_daily (
                    date, avg_bpm, min_bpm, max_bpm, samples_count
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    avg_bpm = excluded.avg_bpm,
                    min_bpm = excluded.min_bpm,
                    max_bpm = excluded.max_bpm,
                    samples_count = excluded.samples_count,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (summary.date, summary.avg_bpm, summary.min_bpm, summary.max_bpm, summary.samples_count),
            )
    return len(summaries), affected


def mirror_health_data_for_dates(dates: set[str]) -> None:
    if not dates:
        return
    from backend.models import upsert_health_data

    ensure_health_importer_schema()
    with get_connection() as conn:
        for date_value in dates:
            sleep = conn.execute("SELECT * FROM health_sleep_daily WHERE date = ?", (date_value,)).fetchone()
            steps = conn.execute("SELECT * FROM health_steps_daily WHERE date = ?", (date_value,)).fetchone()
            heart = conn.execute("SELECT * FROM health_heart_rate_daily WHERE date = ?", (date_value,)).fetchone()
            workout = conn.execute(
                """
                SELECT COALESCE(SUM(active_seconds), 0) AS active_seconds
                FROM health_activities
                WHERE date = ?
                """,
                (date_value,),
            ).fetchone()
            upsert_health_data(
                {
                    "date": date_value,
                    "sleep_hours_auto": round((sleep["total_sleep_seconds"] if sleep else 0) / 3600, 2),
                    "steps_auto": steps["total_steps"] if steps else 0,
                    "workout_minutes_auto": round((workout["active_seconds"] if workout else 0) / 60),
                    "average_heart_rate": heart["avg_bpm"] if heart else 0,
                    "resting_heart_rate": 0,
                    "stress_average": 0,
                    "weight_kg": 0,
                    "source": "Health Sync",
                    "observation": "Importado localmente do Health Sync via Google Drive.",
                }
            )


def latest_import_row() -> dict | None:
    ensure_health_importer_schema()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM health_imported_files
            ORDER BY imported_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
    return dict(row) if row else None


def last_import_logs(limit: int = 12) -> list[dict]:
    ensure_health_importer_schema()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT file_name, data_type, imported_at, rows_imported, status, error_message
            FROM health_imported_files
            ORDER BY imported_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def import_file_stats() -> dict:
    ensure_health_importer_schema()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM health_imported_files
            GROUP BY status
            """
        ).fetchall()
    stats = {"total": 0, "success": 0, "partial": 0, "error": 0}
    for row in rows:
        status = row["status"] or "success"
        stats[status] = int(row["total"])
        stats["total"] += int(row["total"])
    return stats


def health_dashboard(reference_date: str | None = None) -> dict:
    ensure_health_importer_schema()
    today = _parse_reference_date(reference_date)
    start = today - timedelta(days=6)
    dates = [(start + timedelta(days=index)).isoformat() for index in range(7)]
    with get_connection() as conn:
        sleep_rows = _rows_by_date(conn, "health_sleep_daily", dates)
        step_rows = _rows_by_date(conn, "health_steps_daily", dates)
        hr_rows = _rows_by_date(conn, "health_heart_rate_daily", dates)
        activities = conn.execute(
            """
            SELECT * FROM health_activities
            WHERE date BETWEEN ? AND ?
            ORDER BY date DESC, start_time DESC, id DESC
            """,
            (dates[0], dates[-1]),
        ).fetchall()
        last_activity = conn.execute(
            """
            SELECT * FROM health_activities
            ORDER BY date DESC, start_time DESC, id DESC
            LIMIT 1
            """
        ).fetchone()

    activity_by_date: dict[str, list[dict]] = {date_value: [] for date_value in dates}
    for row in activities:
        activity_by_date[row["date"]].append(dict(row))

    daily = []
    for date_value in reversed(dates):
        sleep = sleep_rows.get(date_value)
        steps = step_rows.get(date_value)
        heart = hr_rows.get(date_value)
        day_activities = activity_by_date.get(date_value, [])
        primary_activity = day_activities[0] if day_activities else None
        daily.append(
            {
                "date": date_value,
                "sleep": _sleep_payload(sleep),
                "sleep_seconds": sleep["total_sleep_seconds"] if sleep else 0,
                "steps": steps["total_steps"] if steps else 0,
                "steps_summary": _steps_payload(steps),
                "steps_total": steps["total_steps"] if steps else 0,
                "steps_value": steps["total_steps"] if steps else 0,
                "activities_count": len(day_activities),
                "activity_minutes": round(sum(item["active_seconds"] for item in day_activities) / 60),
                "workout": _workout_payload(primary_activity),
                "heart_rate": _heart_payload(heart),
                "avg_bpm": heart["avg_bpm"] if heart else 0,
            }
        )

    today_row = daily[0] if daily and daily[0]["date"] == today.isoformat() else next(
        (row for row in daily if row["date"] == today.isoformat()),
        {
            "date": today.isoformat(),
            "sleep": _sleep_payload(None),
            "sleep_seconds": 0,
            "steps": 0,
            "steps_summary": _steps_payload(None),
            "steps_total": 0,
            "workout": _workout_payload(None),
            "heart_rate": _heart_payload(None),
            "avg_bpm": 0,
            "activities_count": 0,
        },
    )
    yesterday_row = daily[1] if len(daily) > 1 else None
    today_row["steps_summary"]["difference_from_yesterday"] = (
        today_row["steps_summary"]["total_steps"] - yesterday_row["steps_summary"]["total_steps"]
        if yesterday_row and today_row["steps_summary"]["has_data"] and yesterday_row["steps_summary"]["has_data"]
        else None
    )
    return {
        "today": today_row,
        "last_activity": _workout_payload(dict(last_activity) if last_activity else None),
        "daily": daily,
        "insights": _build_insights(daily)[:3],
        "logs": last_import_logs(),
    }


def _sleep_payload(row) -> dict:
    return {
        "has_data": row is not None,
        "total_sleep_seconds": row["total_sleep_seconds"] if row else 0,
        "light_sleep_seconds": row["light_sleep_seconds"] if row else 0,
        "deep_sleep_seconds": row["deep_sleep_seconds"] if row else 0,
        "rem_sleep_seconds": row["rem_sleep_seconds"] if row else 0,
        "awake_seconds": row["awake_seconds"] if row else 0,
    }


def _steps_payload(row) -> dict:
    return {
        "has_data": row is not None,
        "total_steps": row["total_steps"] if row else 0,
    }


def _heart_payload(row) -> dict:
    return {
        "has_data": row is not None,
        "avg_bpm": row["avg_bpm"] if row else 0,
        "min_bpm": row["min_bpm"] if row else 0,
        "max_bpm": row["max_bpm"] if row else 0,
        "samples_count": row["samples_count"] if row else 0,
    }


def _workout_payload(row) -> dict:
    if not row:
        return {
            "has_data": False,
            "date": "",
            "start_time": "",
            "activity_type": "",
            "activity_name": "",
            "label": "",
            "elapsed_seconds": 0,
            "active_seconds": 0,
            "distance_km": 0,
        }
    label = row.get("activity_name") or row.get("activity_type") or "Treino"
    return {
        "has_data": True,
        "date": row.get("date", ""),
        "start_time": row.get("start_time", ""),
        "activity_type": row.get("activity_type", ""),
        "activity_name": row.get("activity_name", ""),
        "label": label,
        "elapsed_seconds": row.get("elapsed_seconds", 0),
        "active_seconds": row.get("active_seconds", 0),
        "distance_km": row.get("distance_km", 0),
    }


def _rebuild_sleep_summary(conn, date_value: str) -> None:
    rows = conn.execute(
        "SELECT payload_json FROM health_import_records WHERE data_type = 'sleep' AND date = ?",
        (date_value,),
    ).fetchall()
    stages = {"light": 0, "deep": 0, "rem": 0, "awake": 0}
    for row in rows:
        payload = json.loads(row["payload_json"])
        stages[payload.get("stage", "light")] = stages.get(payload.get("stage", "light"), 0) + int(
            payload.get("duration_seconds") or 0
        )
    conn.execute(
        """
        INSERT INTO health_sleep_daily (
            date, total_sleep_seconds, light_sleep_seconds, deep_sleep_seconds,
            rem_sleep_seconds, awake_seconds
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            total_sleep_seconds = excluded.total_sleep_seconds,
            light_sleep_seconds = excluded.light_sleep_seconds,
            deep_sleep_seconds = excluded.deep_sleep_seconds,
            rem_sleep_seconds = excluded.rem_sleep_seconds,
            awake_seconds = excluded.awake_seconds,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            date_value,
            stages["light"] + stages["deep"] + stages["rem"],
            stages["light"],
            stages["deep"],
            stages["rem"],
            stages["awake"],
        ),
    )


def _rebuild_steps_summary(conn, date_value: str) -> None:
    rows = conn.execute(
        "SELECT payload_json FROM health_import_records WHERE data_type = 'steps' AND date = ?",
        (date_value,),
    ).fetchall()
    total = sum(int(json.loads(row["payload_json"]).get("steps") or 0) for row in rows)
    conn.execute(
        """
        INSERT INTO health_steps_daily (date, total_steps)
        VALUES (?, ?)
        ON CONFLICT(date) DO UPDATE SET
            total_steps = excluded.total_steps,
            updated_at = CURRENT_TIMESTAMP
        """,
        (date_value, total),
    )


def _rows_by_date(conn, table: str, dates: list[str]) -> dict:
    placeholders = ",".join("?" for _ in dates)
    rows = conn.execute(f"SELECT * FROM {table} WHERE date IN ({placeholders})", dates).fetchall()
    return {row["date"]: row for row in rows}


def _build_insights(daily: list[dict]) -> list[str]:
    if not daily:
        return []
    insights = []
    today = daily[0]
    yesterday = daily[1] if len(daily) > 1 else None
    today_sleep = today.get("sleep_seconds", 0)
    yesterday_sleep = yesterday.get("sleep_seconds", 0) if yesterday else 0
    today_steps = today.get("steps_total", today.get("steps", 0))
    yesterday_steps = yesterday.get("steps_total", yesterday.get("steps", 0)) if yesterday else 0
    if today_sleep and yesterday_sleep and today_sleep < yesterday_sleep:
        insights.append("Seu sono foi menor hoje. Talvez valha deixar o plano do dia mais leve.")
    if today["activities_count"]:
        insights.append("Voce treinou hoje. Esse dado sera usado no resumo semanal.")
    if yesterday and today_steps > yesterday_steps:
        insights.append("Hoje voce teve mais passos do que ontem.")
    if not insights:
        insights.append("Dados do relogio entram aqui como pistas de rotina, sem analise medica.")
    return insights


def _parse_reference_date(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _sleep_key(record) -> str:
    return f"sleep|{record.date}|{record.stage}|{record.start_time}|{record.duration_seconds}"


def _steps_key(record) -> str:
    return f"steps|{record.date}|{record.time}|{record.steps}"


HEALTH_IMPORTER_SCHEMA = """
CREATE TABLE IF NOT EXISTS health_imported_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    data_type TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rows_imported INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT NOT NULL DEFAULT '',
    UNIQUE(file_hash, data_type)
);

CREATE TABLE IF NOT EXISTS health_import_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_key TEXT NOT NULL UNIQUE,
    data_type TEXT NOT NULL,
    date TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    source_file TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_sleep_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    total_sleep_seconds INTEGER NOT NULL DEFAULT 0,
    light_sleep_seconds INTEGER NOT NULL DEFAULT 0,
    deep_sleep_seconds INTEGER NOT NULL DEFAULT 0,
    rem_sleep_seconds INTEGER NOT NULL DEFAULT 0,
    awake_seconds INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_steps_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    total_steps INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL DEFAULT '',
    activity_type TEXT NOT NULL DEFAULT '',
    activity_name TEXT NOT NULL DEFAULT '',
    elapsed_seconds INTEGER NOT NULL DEFAULT 0,
    active_seconds INTEGER NOT NULL DEFAULT 0,
    distance_km REAL NOT NULL DEFAULT 0,
    source_file TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, start_time, activity_type, elapsed_seconds, distance_km)
);

CREATE TABLE IF NOT EXISTS health_heart_rate_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    avg_bpm INTEGER NOT NULL DEFAULT 0,
    min_bpm INTEGER NOT NULL DEFAULT 0,
    max_bpm INTEGER NOT NULL DEFAULT 0,
    samples_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_health_import_records_date ON health_import_records(date);
CREATE INDEX IF NOT EXISTS idx_health_activities_date ON health_activities(date);
"""
