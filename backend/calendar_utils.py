from __future__ import annotations

import calendar
from datetime import date, datetime

from .database import get_connection


def get_month_calendar(year: int, month: int) -> dict:
    first_day = date(year, month, 1)
    _, days_in_month = calendar.monthrange(year, month)
    start = first_day.isoformat()
    end = date(year, month, days_in_month).isoformat()

    with get_connection() as conn:
        daily_rows = conn.execute(
            "SELECT * FROM daily_records WHERE date >= ? AND date <= ?",
            (start, end),
        ).fetchall()
        nutrition_rows = conn.execute(
            "SELECT * FROM nutrition_records WHERE date >= ? AND date <= ?",
            (start, end),
        ).fetchall()
        focus_rows = conn.execute(
            """
            SELECT date, COUNT(*) AS sessions
            FROM focus_sessions
            WHERE completed = 1 AND date >= ? AND date <= ?
            GROUP BY date
            """,
            (start, end),
        ).fetchall()
        project_rows = conn.execute(
            """
            SELECT date, COALESCE(SUM(minutes), 0) AS minutes
            FROM project_time_entries
            WHERE date >= ? AND date <= ?
            GROUP BY date
            """,
            (start, end),
        ).fetchall()

    daily = {row["date"]: dict(row) for row in daily_rows}
    nutrition = {row["date"]: dict(row) for row in nutrition_rows}
    focus = {row["date"]: int(row["sessions"] or 0) for row in focus_rows}
    projects = {row["date"]: int(row["minutes"] or 0) for row in project_rows}

    days = []
    for day in range(1, days_in_month + 1):
        current = date(year, month, day)
        key = current.isoformat()
        daily_record = daily.get(key)
        nutrition_record = nutrition.get(key)
        score = float(daily_record["daily_score"]) if daily_record else None
        days.append(
            {
                "date": key,
                "day": day,
                "weekday": current.weekday(),
                "score": score,
                "score_class": _score_class(score),
                "has_record": daily_record is not None,
                "daily": daily_record,
                "nutrition": nutrition_record,
                "focus_sessions": focus.get(key, 0),
                "project_minutes": projects.get(key, 0),
                "indicators": {
                    "workout": bool(daily_record and daily_record["workout_done"]),
                    "study": bool(daily_record and daily_record["study_done"]),
                    "programming": bool(daily_record and daily_record["programming_done"]),
                    "reading": bool(daily_record and daily_record["reading_done"]),
                    "nutrition_good": bool(nutrition_record and nutrition_record["nutrition_score"] >= 70),
                    "focus": focus.get(key, 0) > 0,
                },
            }
        )

    return {
        "year": year,
        "month": month,
        "month_label": first_day.strftime("%m/%Y"),
        "first_weekday": first_day.weekday(),
        "days": days,
    }


def parse_month_param(value: str | None) -> tuple[int, int]:
    if not value:
        today = date.today()
        return today.year, today.month
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError:
        today = date.today()
        return today.year, today.month
    return parsed.year, parsed.month


def _score_class(score: float | None) -> str:
    if score is None:
        return "empty"
    if score >= 80:
        return "good"
    if score >= 60:
        return "medium"
    return "low"
