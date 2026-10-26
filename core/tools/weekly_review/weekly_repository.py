from __future__ import annotations

from backend.database import get_connection
from core.tools.focus_mode.focus_repository import summary as focus_summary
from core.tools.focus_mode.focus_repository import top_breakers
from core.tools.monitoring.monitoring_repository import range_summary as monitoring_summary


def daily_records(start: str, end: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM daily_records
            WHERE date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (start, end),
        ).fetchall()
    return [dict(row) for row in rows]


def nutrition_records(start: str, end: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM nutrition_records
            WHERE date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (start, end),
        ).fetchall()
    return [dict(row) for row in rows]


def focus_data(start: str, end: str) -> dict:
    return focus_summary(start, end)


def focus_breakers(start: str, end: str) -> list[dict]:
    return top_breakers(start, end)


def monitoring_data(start: str, end: str) -> dict:
    return monitoring_summary(start, end)


def health_data(start: str, end: str) -> dict:
    with get_connection() as conn:
        sleep = conn.execute(
            "SELECT date, total_sleep_seconds FROM health_sleep_daily WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (start, end),
        ).fetchall()
        steps = conn.execute(
            "SELECT date, total_steps FROM health_steps_daily WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (start, end),
        ).fetchall()
        workouts = conn.execute(
            "SELECT date, activity_type, activity_name, elapsed_seconds, active_seconds FROM health_activities WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (start, end),
        ).fetchall()
        heart = conn.execute(
            "SELECT date, avg_bpm FROM health_heart_rate_daily WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (start, end),
        ).fetchall()
        manual = conn.execute(
            "SELECT date, sleep_hours_auto, steps_auto, workout_minutes_auto, average_heart_rate FROM health_data WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (start, end),
        ).fetchall()
    return {
        "sleep": [dict(row) for row in sleep],
        "steps": [dict(row) for row in steps],
        "workouts": [dict(row) for row in workouts],
        "heart": [dict(row) for row in heart],
        "manual": [dict(row) for row in manual],
    }


def plan_data(start: str, end: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.date, b.*
            FROM daily_plan_blocks b
            JOIN daily_plans p ON p.id = b.plan_id
            WHERE p.date >= ? AND p.date <= ?
            ORDER BY p.date ASC, b.start_time ASC, b.id ASC
            """,
            (start, end),
        ).fetchall()
    return [dict(row) for row in rows]


def saved_review(start: str, end: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM weekly_reviews WHERE week_start = ? AND week_end = ?",
            (start, end),
        ).fetchone()
    return dict(row) if row else None
