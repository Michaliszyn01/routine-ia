from __future__ import annotations

import csv
from datetime import datetime

from .database import EXPORTS_DIR
from .focus_timer import list_focus_sessions
from .models import list_daily_records, list_health_data
from .nutrition import list_nutrition_records
from .projects import list_projects


HISTORY_COLUMNS = [
    "date",
    "weekday",
    "daily_score",
    "workout_done",
    "workout_hours",
    "study_done",
    "study_hours",
    "programming_done",
    "programming_hours",
    "reading_done",
    "reading_hours",
    "sleep_hours",
    "steps",
    "energy",
    "mood",
    "observation",
]

HEALTH_COLUMNS = [
    "date",
    "source",
    "sleep_hours_auto",
    "steps_auto",
    "workout_minutes_auto",
    "average_heart_rate",
    "resting_heart_rate",
    "stress_average",
    "weight_kg",
    "observation",
]

NUTRITION_COLUMNS = [
    "date",
    "nutrition_score",
    "water_liters",
    "breakfast_done",
    "lunch_done",
    "dinner_done",
    "healthy_snack_done",
    "protein_ok",
    "fruits_vegetables_ok",
    "ultra_processed_control",
    "meals_count",
    "observation",
]

FOCUS_COLUMNS = [
    "date",
    "project_name",
    "category",
    "duration_minutes",
    "break_minutes",
    "completed",
    "started_at",
    "ended_at",
    "note",
]

PROJECT_COLUMNS = [
    "id",
    "name",
    "description",
    "category",
    "status",
    "weekly_hours_goal",
    "week_hours",
    "active",
    "created_at",
    "updated_at",
]

PROJECT_TIME_COLUMNS = [
    "date",
    "project_name",
    "minutes",
    "hours",
    "source",
    "note",
    "created_at",
]


def export_history_csv(start: str | None = None, end: str | None = None) -> tuple[str, str]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"routine_ia_history_{timestamp}.csv"
    path = EXPORTS_DIR / filename
    records = list_daily_records(start, end)

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=HISTORY_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    return str(path), filename


def export_health_csv(start: str | None = None, end: str | None = None) -> tuple[str, str]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"routine_ia_health_{timestamp}.csv"
    path = EXPORTS_DIR / filename
    records = list_health_data(start, end)

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=HEALTH_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    return str(path), filename


def export_nutrition_csv(start: str | None = None, end: str | None = None) -> tuple[str, str]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"routine_ia_nutrition_{timestamp}.csv"
    path = EXPORTS_DIR / filename
    records = list_nutrition_records(start, end)
    _write_csv(path, NUTRITION_COLUMNS, records)
    return str(path), filename


def export_focus_csv(start: str | None = None, end: str | None = None) -> tuple[str, str]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"routine_ia_focus_{timestamp}.csv"
    path = EXPORTS_DIR / filename
    records = list_focus_sessions(start, end, limit=10000)
    _write_csv(path, FOCUS_COLUMNS, records)
    return str(path), filename


def export_projects_csv() -> tuple[str, str]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"routine_ia_projects_{timestamp}.csv"
    path = EXPORTS_DIR / filename
    records = list_projects(include_archived=True)
    _write_csv(path, PROJECT_COLUMNS, records)
    return str(path), filename


def export_project_time_csv(start: str | None = None, end: str | None = None) -> tuple[str, str]:
    from .database import get_connection

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"routine_ia_project_time_{timestamp}.csv"
    path = EXPORTS_DIR / filename

    query = """
        SELECT e.date,
               p.name AS project_name,
               e.minutes,
               ROUND(e.minutes / 60.0, 2) AS hours,
               e.source,
               e.note,
               e.created_at
        FROM project_time_entries e
        JOIN projects p ON p.id = e.project_id
    """
    params: list[str] = []
    clauses = []
    if start:
        clauses.append("e.date >= ?")
        params.append(start)
    if end:
        clauses.append("e.date <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY e.date DESC, e.id DESC"

    with get_connection() as conn:
        records = [dict(row) for row in conn.execute(query, params).fetchall()]
    _write_csv(path, PROJECT_TIME_COLUMNS, records)
    return str(path), filename


def _write_csv(path, columns: list[str], records: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

EXPORTABLE_TABLES = {
    "daily_records": ["id", "date", "weekday", "workout_done", "workout_hours", "study_done", "study_hours", "programming_done", "programming_hours", "reading_done", "reading_hours", "sleep_hours", "steps", "energy", "mood", "daily_score", "observation", "created_at", "updated_at"],
    "health_data": ["id", "date", "sleep_hours_auto", "steps_auto", "workout_minutes_auto", "average_heart_rate", "resting_heart_rate", "stress_average", "weight_kg", "source", "observation", "created_at", "updated_at"],
    "life_goals": ["id", "title", "description", "category", "priority", "status", "target_date", "linked_area", "progress_percent", "created_at", "updated_at"],
    "weekly_plans": ["id", "week_start", "week_end", "title", "generated_by", "created_at", "updated_at"],
    "weekly_plan_items": ["id", "plan_id", "date", "weekday", "category", "title", "estimated_minutes", "linked_project_id", "linked_goal_id", "completed", "note", "created_at", "updated_at"],
    "weekly_reviews": ["id", "week_start", "week_end", "what_worked", "what_failed", "best_day", "worst_day", "main_obstacle", "main_win", "next_week_adjustment", "emotional_state", "energy_reflection", "discipline_score", "created_at", "updated_at"],
    "custom_habits": ["id", "name", "description", "category", "frequency", "target_per_week", "weight", "active", "created_at", "updated_at"],
    "habit_logs": ["id", "habit_id", "date", "completed", "value", "note", "created_at"],
    "study_sessions": ["id", "date", "subject", "topic", "duration_minutes", "questions_done", "correct_answers", "wrong_answers", "difficulty", "note", "created_at"],
    "mock_exams": ["id", "date", "exam_name", "area", "score", "total_questions", "correct_answers", "wrong_answers", "essay_score", "note", "created_at"],
    "study_errors": ["id", "date", "subject", "topic", "error_type", "description", "correction", "reviewed", "created_at", "updated_at"],
    "focus_sessions": ["id", "date", "project_id", "category", "duration_minutes", "break_minutes", "completed", "started_at", "ended_at", "note", "created_at"],
    "projects": ["id", "name", "description", "category", "status", "color", "weekly_hours_goal", "active", "created_at", "updated_at"],
    "project_time_entries": ["id", "project_id", "date", "minutes", "source", "note", "created_at"],
    "nutrition_records": ["id", "date", "breakfast_done", "lunch_done", "dinner_done", "healthy_snack_done", "water_liters", "protein_ok", "fruits_vegetables_ok", "ultra_processed_control", "meals_count", "nutrition_score", "observation", "created_at", "updated_at"],
    "weekly_reports": ["id", "week_start", "week_end", "report_text", "score_average", "nutrition_average", "created_at", "updated_at"],
    "bad_day_logs": ["id", "date", "reason", "minimum_actions_done", "note", "created_at"],
    "app_usage_events": ["id", "date", "process_name", "app_name", "window_title", "started_at", "ended_at", "duration_seconds", "category", "productivity_level", "linked_project_id", "created_at"],
    "app_usage_rules": ["id", "process_name", "app_name", "match_type", "window_keyword", "category", "productivity_level", "linked_project_id", "auto_add_to_project_time", "active", "created_at", "updated_at"],
}


def export_table_csv(table_name: str, start: str | None = None, end: str | None = None) -> tuple[str, str]:
    from .database import get_connection

    if table_name not in EXPORTABLE_TABLES:
        raise ValueError("Tabela nao disponivel para exportacao.")
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"routine_ia_{table_name}_{timestamp}.csv"
    path = EXPORTS_DIR / filename
    columns = EXPORTABLE_TABLES[table_name]
    query = f"SELECT {', '.join(columns)} FROM {table_name}"
    params: list[str] = []
    if "date" in columns and (start or end):
        clauses = []
        if start:
            clauses.append("date >= ?")
            params.append(start)
        if end:
            clauses.append("date <= ?")
            params.append(end)
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC"
    with get_connection() as conn:
        rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    _write_csv(path, columns, rows)
    return str(path), filename
