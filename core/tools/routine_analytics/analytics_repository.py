from __future__ import annotations

from datetime import date, datetime, timedelta

from backend import models
from backend.database import get_connection
from core.tools.monitoring.app_rules import score_for_label

from .analytics_schemas import AnalyticsWindow


PRODUCTIVE_LABELS = {"Projeto", "Produtivo", "Estudo"}
RISK_LABELS = {"Risco", "Distracao"}


def resolve_window(period_days: int = 7, reference_date: str | None = None) -> AnalyticsWindow:
    days = period_days if period_days in {7, 14, 30} else 7
    end = _parse_date(reference_date) if reference_date else date.today()
    start = end - timedelta(days=days - 1)
    return AnalyticsWindow(start.isoformat(), end.isoformat(), days)


def combined_daily_rows(period_days: int = 7, reference_date: str | None = None) -> list[dict]:
    window = resolve_window(period_days, reference_date)
    dates = [
        (date.fromisoformat(window.start_date) + timedelta(days=index)).isoformat()
        for index in range(window.period_days)
    ]
    daily_by_date = {row["date"]: row for row in models.list_daily_records(window.start_date, window.end_date)}
    health_by_date = _health_rows(window.start_date, window.end_date)
    usage_by_date = _usage_rows(window.start_date, window.end_date)

    rows = []
    for date_value in reversed(dates):
        daily = daily_by_date.get(date_value) or {}
        health = health_by_date.get(date_value) or {}
        usage = usage_by_date.get(date_value) or {}
        sleep_hours = _first_positive(
            _seconds_to_hours(health.get("sleep_seconds")),
            daily.get("sleep_hours"),
        )
        steps = int(_first_positive(health.get("steps"), daily.get("steps")) or 0)
        health_workout_minutes = round(float(health.get("workout_seconds") or 0) / 60, 1)
        daily_workout_minutes = round(float(daily.get("workout_hours") or 0) * 60, 1)
        workout_minutes = _first_positive(health_workout_minutes, daily_workout_minutes) or 0
        trained = bool(workout_minutes > 0 or int(daily.get("workout_done") or 0))
        productive_minutes = round(float(usage.get("productive_seconds") or 0) / 60, 1)
        risk_minutes = round(float(usage.get("risk_seconds") or 0) / 60, 1)
        total_pc_minutes = round(float(usage.get("total_seconds") or 0) / 60, 1)
        rows.append(
            {
                "date": date_value,
                "sleep_hours": round(float(sleep_hours or 0), 2),
                "sleep_source": "health" if health.get("sleep_seconds") else "daily" if daily.get("sleep_hours") else "",
                "steps": steps,
                "workout_minutes": round(float(workout_minutes or 0), 1),
                "trained": trained,
                "avg_bpm": int(health.get("avg_bpm") or 0),
                "productive_minutes": productive_minutes,
                "risk_minutes": risk_minutes,
                "neutral_minutes": round(float(usage.get("neutral_seconds") or 0) / 60, 1),
                "total_pc_minutes": total_pc_minutes,
                "pc_score": round(float(usage.get("score") or 0), 1),
                "routine_score": round(float(daily.get("daily_score") or 0), 1),
                "energy": int(float(daily.get("energy") or 0)),
                "mood": int(float(daily.get("mood") or 0)),
                "study_hours": round(float(daily.get("study_hours") or 0), 2),
                "programming_hours": round(float(daily.get("programming_hours") or 0), 2),
                "reading_hours": round(float(daily.get("reading_hours") or 0), 2),
                "has_health_data": bool(health),
                "has_pc_data": bool(usage),
                "has_daily_record": bool(daily),
                "good_sleep": float(sleep_hours or 0) >= 7,
                "short_sleep": bool(sleep_hours) and float(sleep_hours or 0) < 6,
                "focus_good": productive_minutes > 0 and productive_minutes >= risk_minutes,
                "risk_high": risk_minutes >= 60 or (risk_minutes > productive_minutes and risk_minutes > 0),
            }
        )
    return rows


def _health_rows(start_date: str, end_date: str) -> dict[str, dict]:
    with get_connection() as conn:
        sleep_rows = conn.execute(
            """
            SELECT date, total_sleep_seconds
            FROM health_sleep_daily
            WHERE date >= ? AND date <= ?
            """,
            (start_date, end_date),
        ).fetchall()
        step_rows = conn.execute(
            """
            SELECT date, total_steps
            FROM health_steps_daily
            WHERE date >= ? AND date <= ?
            """,
            (start_date, end_date),
        ).fetchall()
        workout_rows = conn.execute(
            """
            SELECT date, COALESCE(SUM(active_seconds), 0) AS workout_seconds
            FROM health_activities
            WHERE date >= ? AND date <= ?
            GROUP BY date
            """,
            (start_date, end_date),
        ).fetchall()
        heart_rows = conn.execute(
            """
            SELECT date, avg_bpm
            FROM health_heart_rate_daily
            WHERE date >= ? AND date <= ?
            """,
            (start_date, end_date),
        ).fetchall()

    result: dict[str, dict] = {}
    for row in sleep_rows:
        result.setdefault(row["date"], {})["sleep_seconds"] = int(row["total_sleep_seconds"] or 0)
    for row in step_rows:
        result.setdefault(row["date"], {})["steps"] = int(row["total_steps"] or 0)
    for row in workout_rows:
        result.setdefault(row["date"], {})["workout_seconds"] = int(row["workout_seconds"] or 0)
    for row in heart_rows:
        result.setdefault(row["date"], {})["avg_bpm"] = int(row["avg_bpm"] or 0)
    return result


def _usage_rows(start_date: str, end_date: str) -> dict[str, dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT date, label, total_seconds
            FROM monitoring_app_usage_daily
            WHERE date >= ? AND date <= ?
            """,
            (start_date, end_date),
        ).fetchall()

    result: dict[str, dict] = {}
    for row in rows:
        date_value = row["date"]
        label = row["label"] or "Neutro"
        seconds = int(row["total_seconds"] or 0)
        bucket = result.setdefault(
            date_value,
            {"total_seconds": 0, "productive_seconds": 0, "risk_seconds": 0, "neutral_seconds": 0, "score": 0},
        )
        bucket["total_seconds"] += seconds
        bucket["score"] += seconds * score_for_label(label) / 60
        if label in PRODUCTIVE_LABELS:
            bucket["productive_seconds"] += seconds
        elif label in RISK_LABELS:
            bucket["risk_seconds"] += seconds
        else:
            bucket["neutral_seconds"] += seconds
    return result


def _parse_date(value: str | None) -> date:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return date.today()


def _seconds_to_hours(value) -> float:
    return round(float(value or 0) / 3600, 2)


def _first_positive(*values) -> float:
    for value in values:
        number = float(value or 0)
        if number > 0:
            return number
    return 0

