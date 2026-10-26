from __future__ import annotations

from datetime import date, datetime, timedelta

from .database import DEFAULT_GOALS, DEFAULT_SETTINGS, get_connection
from .scoring import calculate_daily_score
from .validators import (
    bool_to_int,
    validate_daily_payload,
    validate_goal_payload,
    validate_health_payload,
    validate_settings_payload,
)


WEEKDAY_NAMES = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]

SHORT_WEEKDAY_NAMES = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
GOAL_LABELS = {
    "workout": "Treino",
    "study": "Estudo",
    "programming": "Programação",
    "reading": "Leitura",
    "sleep": "Sono",
}


def today_iso() -> str:
    return date.today().isoformat()


def weekday_for(date_value: str) -> str:
    return WEEKDAY_NAMES[_parse_date(date_value).weekday()]


def week_range(reference_date: str | None = None) -> tuple[str, str]:
    current = _parse_date(reference_date or today_iso())
    start = current - timedelta(days=current.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def get_goals() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM goals ORDER BY id").fetchall()
    return [_row_to_dict(row) for row in rows]


def get_goals_by_category() -> dict[str, dict]:
    return {goal["category"]: goal for goal in get_goals()}


def update_goal(category: str, payload: dict) -> dict:
    data = validate_goal_payload(payload)
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM goals WHERE category = ?", (category,)
        ).fetchone()
        if not existing:
            raise ValueError(f"Categoria de meta desconhecida: {category}")
        conn.execute(
            """
            UPDATE goals
            SET weekly_days_goal = ?,
                daily_hours_goal = ?,
                weekly_hours_goal = ?,
                daily_weight = ?,
                max_daily_hours = ?,
                active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE category = ?
            """,
            (
                data["weekly_days_goal"],
                data["daily_hours_goal"],
                data["weekly_hours_goal"],
                data["daily_weight"],
                data["max_daily_hours"],
                data["active"],
                category,
            ),
        )
        row = conn.execute("SELECT * FROM goals WHERE category = ?", (category,)).fetchone()
    return _row_to_dict(row)


def update_goals_bulk(payload: dict | list) -> list[dict]:
    items = payload.get("goals", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Envie uma lista de metas.")

    for item in items:
        category = item.get("category")
        if not category:
            raise ValueError("Categoria de meta obrigatória.")
        update_goal(category, item)

    return get_goals()


def reset_goals_to_default() -> list[dict]:
    with get_connection() as conn:
        for goal in DEFAULT_GOALS:
            conn.execute(
                """
                INSERT INTO goals (
                    category,
                    label,
                    weekly_days_goal,
                    daily_hours_goal,
                    weekly_hours_goal,
                    daily_weight,
                    max_daily_hours,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(category) DO UPDATE SET
                    label = excluded.label,
                    weekly_days_goal = excluded.weekly_days_goal,
                    daily_hours_goal = excluded.daily_hours_goal,
                    weekly_hours_goal = excluded.weekly_hours_goal,
                    daily_weight = excluded.daily_weight,
                    max_daily_hours = excluded.max_daily_hours,
                    active = excluded.active,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    goal["category"],
                    goal["label"],
                    goal["weekly_days_goal"],
                    goal["daily_hours_goal"],
                    goal["weekly_hours_goal"],
                    goal["daily_weight"],
                    goal["max_daily_hours"],
                    goal["active"],
                ),
            )
    return get_goals()


def get_daily_record(date_value: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM daily_records WHERE date = ?", (date_value,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def upsert_daily_record(payload: dict) -> dict:
    data = validate_daily_payload(payload)
    date_value = data["date"]
    data["weekday"] = weekday_for(date_value)
    data["daily_score"] = calculate_daily_score(data, get_goals_by_category())

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO daily_records (
                date,
                weekday,
                workout_done,
                workout_hours,
                study_done,
                study_hours,
                programming_done,
                programming_hours,
                game_hours,
                reading_done,
                reading_hours,
                sleep_hours,
                steps,
                energy,
                mood,
                daily_score,
                observation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                weekday = excluded.weekday,
                workout_done = excluded.workout_done,
                workout_hours = excluded.workout_hours,
                study_done = excluded.study_done,
                study_hours = excluded.study_hours,
                programming_done = excluded.programming_done,
                programming_hours = excluded.programming_hours,
                game_hours = excluded.game_hours,
                reading_done = excluded.reading_done,
                reading_hours = excluded.reading_hours,
                sleep_hours = excluded.sleep_hours,
                steps = excluded.steps,
                energy = excluded.energy,
                mood = excluded.mood,
                daily_score = excluded.daily_score,
                observation = excluded.observation,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                data["date"],
                data["weekday"],
                data["workout_done"],
                data["workout_hours"],
                data["study_done"],
                data["study_hours"],
                data["programming_done"],
                data["programming_hours"],
                data["game_hours"],
                data["reading_done"],
                data["reading_hours"],
                data["sleep_hours"],
                data["steps"],
                data["energy"],
                data["mood"],
                data["daily_score"],
                data["observation"],
            ),
        )
        row = conn.execute(
            "SELECT * FROM daily_records WHERE date = ?", (date_value,)
        ).fetchone()
    try:
        from .streaks import update_streaks_cache

        update_streaks_cache()
    except Exception:
        pass
    return _row_to_dict(row)


def list_daily_records(start: str | None = None, end: str | None = None) -> list[dict]:
    query = "SELECT * FROM daily_records"
    params: list[str] = []
    clauses = []
    if start:
        clauses.append("date >= ?")
        params.append(start)
    if end:
        clauses.append("date <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY date DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def _weekly_dashboard_legacy_v1(reference_date: str | None = None) -> dict:
    start, end = week_range(reference_date)
    records_desc = list_daily_records(start, end)
    records = sorted(records_desc, key=lambda item: item["date"])
    by_date = {record["date"]: record for record in records}
    week_days = [_parse_date(start) + timedelta(days=index) for index in range(7)]
    labels = [SHORT_WEEKDAY_NAMES[index] for index in range(7)]

    score_values = []
    sleep_values = []
    energy_values = []
    mood_values = []
    steps_values = []
    for day in week_days:
        record = by_date.get(day.isoformat())
        score_values.append(float(record["daily_score"]) if record else 0)
        sleep_values.append(float(record["sleep_hours"]) if record else 0)
        energy_values.append(int(record["energy"]) if record else 0)
        mood_values.append(int(record["mood"]) if record else 0)
        steps_values.append(int(record["steps"]) if record else 0)

    today_record = get_daily_record(today_iso())
    recorded_count = len(records)
    sleep_entries = [float(record["sleep_hours"]) for record in records if record["sleep_hours"] > 0]
    energy_entries = [int(record["energy"]) for record in records]
    mood_entries = [int(record["mood"]) for record in records]

    hours_by_category = {
        "Treino": _sum(records, "workout_hours"),
        "Estudo": _sum(records, "study_hours"),
        "Programação": _sum(records, "programming_hours"),
        "Leitura": _sum(records, "reading_hours"),
    }
    goals = get_goals()
    weight_total = sum(float(goal["daily_weight"]) for goal in goals if goal["active"])
    best_day = max(records, key=lambda item: float(item["daily_score"]), default=None)
    worst_day = min(records, key=lambda item: float(item["daily_score"]), default=None)

    return {
        "week_start": start,
        "week_end": end,
        "today": today_iso(),
        "summary": {
            "average_score": _avg([float(record["daily_score"]) for record in records]),
            "today_score": float(today_record["daily_score"]) if today_record else 0,
            "workout_days": _count_done(records, "workout_done"),
            "study_days": _count_done(records, "study_done"),
            "programming_days": _count_done(records, "programming_done"),
            "reading_days": _count_done(records, "reading_done"),
            "average_sleep": _avg(sleep_entries),
            "total_steps": int(_sum(records, "steps")),
            "average_energy": _avg(energy_entries),
            "average_mood": _avg(mood_entries),
            "recorded_days": recorded_count,
            "active_weight_total": round(weight_total, 2),
            "best_day": _day_score_summary(best_day),
            "worst_day": _day_score_summary(worst_day),
        },
        "charts": {
            "labels": labels,
            "score_by_day": score_values,
            "sleep_by_day": sleep_values,
            "energy_by_day": energy_values,
            "mood_by_day": mood_values,
            "steps_by_day": steps_values,
            "hours_by_category": hours_by_category,
        },
        "goals": goals,
    }


def _history_summary_legacy_v1(start: str | None = None, end: str | None = None) -> dict:
    records = list_daily_records(start, end)
    sleep_entries = [float(record["sleep_hours"]) for record in records if record["sleep_hours"] > 0]
    energy_entries = [int(record["energy"]) for record in records]
    mood_entries = [int(record["mood"]) for record in records]

    return {
        "record_count": len(records),
        "average_score": _avg([float(record["daily_score"]) for record in records]),
        "total_workout_hours": _sum(records, "workout_hours"),
        "total_study_hours": _sum(records, "study_hours"),
        "total_programming_hours": _sum(records, "programming_hours"),
        "total_reading_hours": _sum(records, "reading_hours"),
        "average_sleep": _avg(sleep_entries),
        "total_steps": int(_sum(records, "steps")),
        "average_energy": _avg(energy_entries),
        "average_mood": _avg(mood_entries),
    }


def upsert_health_data(payload: dict) -> dict:
    data = validate_health_payload(payload)
    date_value = data["date"]
    source = data["source"]
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO health_data (
                date,
                sleep_hours_auto,
                steps_auto,
                workout_minutes_auto,
                average_heart_rate,
                resting_heart_rate,
                stress_average,
                weight_kg,
                source,
                observation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, source) DO UPDATE SET
                sleep_hours_auto = excluded.sleep_hours_auto,
                steps_auto = excluded.steps_auto,
                workout_minutes_auto = excluded.workout_minutes_auto,
                average_heart_rate = excluded.average_heart_rate,
                resting_heart_rate = excluded.resting_heart_rate,
                stress_average = excluded.stress_average,
                weight_kg = excluded.weight_kg,
                observation = excluded.observation,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                data["date"],
                data["sleep_hours_auto"],
                data["steps_auto"],
                data["workout_minutes_auto"],
                data["average_heart_rate"],
                data["resting_heart_rate"],
                data["stress_average"],
                data["weight_kg"],
                data["source"],
                data["observation"],
            ),
        )
        row = conn.execute(
            "SELECT * FROM health_data WHERE date = ? AND source = ?",
            (date_value, source),
        ).fetchone()
    return _row_to_dict(row)


def list_health_data(start: str | None = None, end: str | None = None) -> list[dict]:
    query = "SELECT * FROM health_data"
    params: list[str] = []
    clauses = []
    if start:
        clauses.append("date >= ?")
        params.append(start)
    if end:
        clauses.append("date <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY date DESC, source ASC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_settings() -> dict[str, str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    settings = dict(DEFAULT_SETTINGS)
    settings.update({row["key"]: row["value"] for row in rows})
    return settings


def update_settings(payload: dict) -> dict[str, str]:
    data = validate_settings_payload(payload)
    with get_connection() as conn:
        for key, value in data.items():
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
    _sync_startup_from_settings(data)
    return get_settings()


def set_settings_values(values: dict[str, str]) -> dict[str, str]:
    allowed_keys = set(DEFAULT_SETTINGS)
    cleaned = {key: str(value) for key, value in values.items() if key in allowed_keys}
    if not cleaned:
        return get_settings()
    with get_connection() as conn:
        for key, value in cleaned.items():
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
    return get_settings()


def reset_settings_to_default() -> dict[str, str]:
    with get_connection() as conn:
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
    _sync_startup_from_settings(DEFAULT_SETTINGS)
    return get_settings()


def get_setting_bool(key: str, default: bool = False) -> bool:
    value = get_settings().get(key)
    if value is None:
        return default
    return bool(bool_to_int(value))


def get_setting_int(key: str, default: int = 0) -> int:
    try:
        return int(float(get_settings().get(key, default)))
    except (TypeError, ValueError):
        return default


def _sync_startup_from_settings(settings: dict[str, str]) -> None:
    try:
        from .startup import sync_startup_shortcut

        sync_startup_shortcut(
            settings.get("start_with_windows") == "true",
            start_minimized=settings.get("start_minimized") == "true",
        )
    except Exception:
        pass


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _row_to_dict(row) -> dict:
    return dict(row)


def _bool_to_int(value) -> int:
    return bool_to_int(value)


def _non_negative_float(value, default: float = 0) -> float:
    try:
        return max(float(value), 0)
    except (TypeError, ValueError):
        return default


def _non_negative_int(value, default: int = 0) -> int:
    try:
        return max(int(float(value)), 0)
    except (TypeError, ValueError):
        return default


def _clamp_int(value, minimum: int, maximum: int, default: int = 0) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def _sum(records: list[dict], key: str) -> float:
    return round(sum(float(record.get(key) or 0) for record in records), 2)


def _avg(values: list[float | int]) -> float:
    clean_values = [float(value) for value in values if value is not None]
    if not clean_values:
        return 0
    return round(sum(clean_values) / len(clean_values), 2)


def _count_done(records: list[dict], key: str) -> int:
    return sum(1 for record in records if int(record.get(key) or 0))


def _day_score_summary(record: dict | None) -> dict | None:
    if not record:
        return None
    return {
        "date": record["date"],
        "weekday": record["weekday"],
        "daily_score": float(record["daily_score"]),
    }


# V2 composition helpers. They keep the original public API intact while
# enriching dashboard/history/today responses with the new modules.
def _weekly_dashboard_core(reference_date: str | None = None) -> dict:
    from .focus_timer import focus_summary
    from .insights import get_week_comparison
    from .nutrition import nutrition_energy_correlation, weekly_nutrition_summary
    from .projects import project_summary
    from .streaks import get_all_streaks

    start, end = week_range(reference_date)
    records_desc = list_daily_records(start, end)
    records = sorted(records_desc, key=lambda item: item["date"])
    by_date = {record["date"]: record for record in records}
    week_days = [_parse_date(start) + timedelta(days=index) for index in range(7)]
    labels = [SHORT_WEEKDAY_NAMES[index] for index in range(7)]

    score_values = []
    sleep_values = []
    energy_values = []
    mood_values = []
    steps_values = []
    for day in week_days:
        record = by_date.get(day.isoformat())
        score_values.append(float(record["daily_score"]) if record else 0)
        sleep_values.append(float(record["sleep_hours"]) if record else 0)
        energy_values.append(int(record["energy"]) if record else 0)
        mood_values.append(int(record["mood"]) if record else 0)
        steps_values.append(int(record["steps"]) if record else 0)

    today_record = get_daily_record(today_iso())
    recorded_count = len(records)
    sleep_entries = [float(record["sleep_hours"]) for record in records if record["sleep_hours"] > 0]
    energy_entries = [int(record["energy"]) for record in records]
    mood_entries = [int(record["mood"]) for record in records]
    goals = get_goals()
    weight_total = sum(float(goal["daily_weight"]) for goal in goals if goal["active"])
    best_day = max(records, key=lambda item: float(item["daily_score"]), default=None)
    worst_day = min(records, key=lambda item: float(item["daily_score"]), default=None)
    nutrition = weekly_nutrition_summary(reference_date)
    focus = focus_summary(start, end)
    projects = project_summary(reference_date)
    focus_by_day = []
    for day in week_days:
        focus_by_day.append(round(focus["by_date"].get(day.isoformat(), 0) / 60, 2))

    return {
        "week_start": start,
        "week_end": end,
        "today": today_iso(),
        "summary": {
            "average_score": _avg([float(record["daily_score"]) for record in records]),
            "today_score": float(today_record["daily_score"]) if today_record else 0,
            "workout_days": _count_done(records, "workout_done"),
            "study_days": _count_done(records, "study_done"),
            "programming_days": _count_done(records, "programming_done"),
            "reading_days": _count_done(records, "reading_done"),
            "average_sleep": _avg(sleep_entries),
            "total_steps": int(_sum(records, "steps")),
            "average_energy": _avg(energy_entries),
            "average_mood": _avg(mood_entries),
            "recorded_days": recorded_count,
            "active_weight_total": round(weight_total, 2),
            "best_day": _day_score_summary(best_day),
            "worst_day": _day_score_summary(worst_day),
            "nutrition_average": nutrition["average_score"],
            "water_average": nutrition["average_water"],
            "protein_days": nutrition["protein_days"],
            "hydration_good_days": nutrition["hydration_good_days"],
            "focus_sessions": focus["sessions"],
            "focus_hours": focus["hours"],
            "active_projects": projects["active_projects"],
            "project_hours": projects["total_hours"],
            "nutrition_energy": nutrition_energy_correlation(start, end),
        },
        "charts": {
            "labels": labels,
            "score_by_day": score_values,
            "sleep_by_day": sleep_values,
            "energy_by_day": energy_values,
            "mood_by_day": mood_values,
            "steps_by_day": steps_values,
            "hours_by_category": {
                "Treino": _sum(records, "workout_hours"),
                "Estudo": _sum(records, "study_hours"),
                "Programacao": _sum(records, "programming_hours"),
                "Leitura": _sum(records, "reading_hours"),
            },
            "nutrition_by_day": nutrition["score_by_day"],
            "water_by_day": nutrition["water_by_day"],
            "focus_by_day": focus_by_day,
            "hours_by_project": projects["hours_by_project"],
        },
        "goals": goals,
        "nutrition": nutrition,
        "focus": focus,
        "projects": projects,
        "streaks": get_all_streaks(),
        "comparison": get_week_comparison(start),
    }


def history_summary(start: str | None = None, end: str | None = None) -> dict:
    from .nutrition import nutrition_summary

    records = list_daily_records(start, end)
    sleep_entries = [float(record["sleep_hours"]) for record in records if record["sleep_hours"] > 0]
    energy_entries = [int(record["energy"]) for record in records]
    mood_entries = [int(record["mood"]) for record in records]
    nutrition = nutrition_summary(start, end)

    return {
        "record_count": len(records),
        "average_score": _avg([float(record["daily_score"]) for record in records]),
        "total_workout_hours": _sum(records, "workout_hours"),
        "total_study_hours": _sum(records, "study_hours"),
        "total_programming_hours": _sum(records, "programming_hours"),
        "total_reading_hours": _sum(records, "reading_hours"),
        "average_sleep": _avg(sleep_entries),
        "total_steps": int(_sum(records, "steps")),
        "average_energy": _avg(energy_entries),
        "average_mood": _avg(mood_entries),
        "nutrition_average": nutrition["average_score"],
        "water_average": nutrition["average_water"],
        "protein_days": nutrition["protein_days"],
        "fruits_vegetables_days": nutrition["fruits_vegetables_days"],
    }


def _get_today_bundle_core(date_value: str | None = None) -> dict:
    from .nutrition import get_nutrition_record
    from .streaks import get_all_streaks

    date_value = date_value or today_iso()
    daily = get_daily_record(date_value)
    nutrition = get_nutrition_record(date_value)
    return {
        "date": date_value,
        "weekday": weekday_for(date_value),
        "editing": daily is not None or nutrition is not None,
        "daily": daily,
        "nutrition": nutrition,
        "streaks": get_all_streaks(),
    }


def save_today_bundle(payload: dict) -> dict:
    from .nutrition import upsert_nutrition_record
    from .streaks import update_streaks_cache

    date_value = payload.get("date") or payload.get("daily", {}).get("date") or today_iso()
    daily_payload = dict(payload.get("daily") or _extract_fields(payload, DAILY_FIELDS))
    nutrition_payload = dict(payload.get("nutrition") or _extract_fields(payload, NUTRITION_FIELDS))
    daily_payload["date"] = date_value
    nutrition_payload["date"] = date_value
    daily = upsert_daily_record(daily_payload)
    nutrition = upsert_nutrition_record(nutrition_payload)
    update_streaks_cache()
    return {
        "ok": True,
        "date": date_value,
        "weekday": weekday_for(date_value),
        "daily": daily,
        "nutrition": nutrition,
    }


DAILY_FIELDS = {
    "workout_done",
    "workout_hours",
    "study_done",
    "study_hours",
    "programming_done",
    "programming_hours",
    "game_hours",
    "reading_done",
    "reading_hours",
    "sleep_hours",
    "steps",
    "energy",
    "mood",
    "observation",
}

NUTRITION_FIELDS = {
    "breakfast_done",
    "lunch_done",
    "dinner_done",
    "healthy_snack_done",
    "water_liters",
    "protein_ok",
    "fruits_vegetables_ok",
    "ultra_processed_control",
    "meals_count",
    "observation",
}


def _extract_fields(payload: dict, fields: set[str]) -> dict:
    return {field: payload.get(field) for field in fields if field in payload}

# V3 Life OS composition. This wraps the V2 dashboard/today bundle without
# changing older routes or payloads.
_weekly_dashboard_v2 = _weekly_dashboard_core
_get_today_bundle_v2 = _get_today_bundle_core


def _weekly_dashboard_life_os(reference_date: str | None = None) -> dict:
    data = _weekly_dashboard_v2(reference_date)
    from .alerts import get_alerts
    from .life_os import bad_day_summary, habit_summary, life_goal_summary, study_summary
    from .load_balance import get_load_balance
    from .patterns import detect_patterns

    life_goals = life_goal_summary(reference_date)
    habits = habit_summary(data["week_start"], data["week_end"])
    studies = study_summary(data["week_start"], data["week_end"])
    load = get_load_balance(reference_date)
    patterns = detect_patterns(data["week_start"], data["week_end"])
    alerts = get_alerts(reference_date)
    bad_days = bad_day_summary(data["week_start"], data["week_end"])
    data["summary"].update(
        {
            "life_goals_active": life_goals["active_count"],
            "life_goals_average_progress": life_goals["average_progress"],
            "habits_completed": habits["completed_this_week"],
            "habits_active": habits["active_count"],
            "study_session_hours": studies["total_hours"],
            "study_accuracy": studies["accuracy"],
            "load_index": load["index"],
            "load_level": load["level"],
            "active_alerts": alerts["count"],
            "patterns_count": len(patterns.get("patterns", [])),
            "bad_day_count": bad_days["count"],
        }
    )
    data["life_goals"] = life_goals
    data["habits"] = habits
    data["studies"] = studies
    data["load_balance"] = load
    data["patterns"] = patterns
    data["alerts"] = alerts
    data["bad_days"] = bad_days
    return data


def get_today_bundle(date_value: str | None = None) -> dict:
    data = _get_today_bundle_v2(date_value)
    from .alerts import get_alerts
    from .life_os import get_bad_day, get_todays_habits

    data["habits"] = get_todays_habits(data["date"])
    data["bad_day"] = get_bad_day(data["date"])
    data["alerts"] = get_alerts(data["date"])
    return data

# V4 PC usage composition. Keeps prior dashboard payloads intact and adds an
# opt-in local activity summary for the main dashboard.
_weekly_dashboard_v3 = _weekly_dashboard_life_os


def weekly_dashboard(reference_date: str | None = None) -> dict:
    data = _weekly_dashboard_v3(reference_date)
    from core.tools.monitoring.monitoring_repository import daily_summary

    usage_today = daily_summary(data["today"])
    data["summary"].update(
        {
            "pc_productive_minutes": usage_today["productive_minutes"],
            "pc_distraction_minutes": usage_today["distraction_minutes"],
            "pc_total_minutes": usage_today["total_minutes"],
        }
    )
    data["app_usage_today"] = usage_today
    return data
