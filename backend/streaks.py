from __future__ import annotations

from datetime import date, datetime, timedelta

from .database import DEFAULT_STREAK_TYPES, get_connection


STREAK_LABELS = {
    "daily_record": "Registros",
    "workout": "Treino",
    "study": "Estudo",
    "programming": "Programacao",
    "reading": "Leitura",
    "good_sleep": "Sono bom",
    "good_score": "Score 70+",
    "nutrition_good": "Alimentacao boa",
    "hydration_good": "Hidratacao boa",
    "focus_sessions": "Foco",
}


def calculate_current_streak(streak_type: str) -> int:
    valid_dates = _valid_dates(streak_type)
    if not valid_dates:
        return 0

    cursor = date.today()
    if cursor not in valid_dates:
        yesterday = cursor - timedelta(days=1)
        if yesterday not in valid_dates:
            return 0
        cursor = yesterday

    count = 0
    while cursor in valid_dates:
        count += 1
        cursor -= timedelta(days=1)
    return count


def calculate_best_streak(streak_type: str) -> int:
    dates = sorted(_valid_dates(streak_type))
    if not dates:
        return 0
    best = 1
    current = 1
    for previous, item in zip(dates, dates[1:]):
        if item == previous + timedelta(days=1):
            current += 1
        else:
            current = 1
        best = max(best, current)
    return best


def get_all_streaks() -> dict:
    update_streaks_cache()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM streaks_cache
            ORDER BY CASE streak_type
                WHEN 'daily_record' THEN 1
                WHEN 'study' THEN 2
                WHEN 'programming' THEN 3
                WHEN 'workout' THEN 4
                WHEN 'nutrition_good' THEN 5
                WHEN 'hydration_good' THEN 6
                WHEN 'focus_sessions' THEN 7
                ELSE 99
            END
            """
        ).fetchall()
    items = []
    for row in rows:
        data = dict(row)
        data["label"] = STREAK_LABELS.get(data["streak_type"], data["streak_type"])
        items.append(data)
    best = max(items, key=lambda item: int(item["best_count"] or 0), default=None)
    return {
        "streaks": items,
        "main": next((item for item in items if item["streak_type"] == "daily_record"), None),
        "best": best,
    }


def update_streaks_cache() -> None:
    with get_connection() as conn:
        for streak_type in DEFAULT_STREAK_TYPES:
            valid_dates = _valid_dates(streak_type)
            last_valid = max(valid_dates).isoformat() if valid_dates else ""
            conn.execute(
                """
                INSERT INTO streaks_cache (
                    streak_type, current_count, best_count, last_valid_date, updated_at
                )
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(streak_type) DO UPDATE SET
                    current_count = excluded.current_count,
                    best_count = excluded.best_count,
                    last_valid_date = excluded.last_valid_date,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    streak_type,
                    _current_from_dates(valid_dates),
                    _best_from_dates(valid_dates),
                    last_valid,
                ),
            )


def _valid_dates(streak_type: str) -> set[date]:
    query = _query_for(streak_type)
    if not query:
        return set()
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return {_parse_date(row["date"]) for row in rows if row["date"]}


def _query_for(streak_type: str) -> str | None:
    queries = {
        "daily_record": "SELECT date FROM daily_records",
        "workout": "SELECT date FROM daily_records WHERE workout_done = 1",
        "study": "SELECT date FROM daily_records WHERE study_done = 1",
        "programming": "SELECT date FROM daily_records WHERE programming_done = 1",
        "reading": "SELECT date FROM daily_records WHERE reading_done = 1",
        "good_sleep": "SELECT date FROM daily_records WHERE sleep_hours >= 7",
        "good_score": "SELECT date FROM daily_records WHERE daily_score >= 70",
        "nutrition_good": "SELECT date FROM nutrition_records WHERE nutrition_score >= 70",
        "hydration_good": "SELECT date FROM nutrition_records WHERE water_liters >= 2",
        "focus_sessions": "SELECT DISTINCT date FROM focus_sessions WHERE completed = 1",
    }
    return queries.get(streak_type)


def _current_from_dates(valid_dates: set[date]) -> int:
    if not valid_dates:
        return 0
    cursor = date.today()
    if cursor not in valid_dates:
        yesterday = cursor - timedelta(days=1)
        if yesterday not in valid_dates:
            return 0
        cursor = yesterday
    count = 0
    while cursor in valid_dates:
        count += 1
        cursor -= timedelta(days=1)
    return count


def _best_from_dates(valid_dates: set[date]) -> int:
    dates = sorted(valid_dates)
    if not dates:
        return 0
    best = 1
    current = 1
    for previous, item in zip(dates, dates[1:]):
        if item == previous + timedelta(days=1):
            current += 1
        else:
            current = 1
        best = max(best, current)
    return best


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
