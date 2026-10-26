from __future__ import annotations

from datetime import datetime, timedelta

from .focus_timer import focus_summary
from .models import list_daily_records, week_range
from .nutrition import nutrition_summary
from .projects import hours_by_project


def get_week_comparison(current_week_start: str | None = None) -> dict:
    current_start, current_end = week_range(current_week_start)
    previous_start_date = _parse_date(current_start) - timedelta(days=7)
    previous_start = previous_start_date.isoformat()
    previous_end = (previous_start_date + timedelta(days=6)).isoformat()

    current = _week_metrics(current_start, current_end)
    previous = _week_metrics(previous_start, previous_end)
    metrics = {}
    for key, label in METRIC_LABELS.items():
        metrics[key] = _compare_metric(
            label,
            current.get(key, 0),
            previous.get(key, 0),
            lower_is_better=key in {"ultra_processed_days"},
        )

    return {
        "current_week": {"start": current_start, "end": current_end},
        "previous_week": {"start": previous_start, "end": previous_end},
        "metrics": metrics,
        "project_hours": {
            "current": hours_by_project(current_start, current_end),
            "previous": hours_by_project(previous_start, previous_end),
        },
    }


METRIC_LABELS = {
    "average_score": "Pontuacao media",
    "workout_hours": "Horas de treino",
    "study_hours": "Horas de estudo",
    "programming_hours": "Horas de programacao",
    "reading_hours": "Horas de leitura",
    "average_sleep": "Sono medio",
    "total_steps": "Passos totais",
    "average_energy": "Energia media",
    "average_mood": "Humor medio",
    "nutrition_average": "Nota alimentar media",
    "water_average": "Agua media",
    "focus_sessions": "Sessoes de foco",
    "focus_hours": "Horas de foco",
}


def _week_metrics(start: str, end: str) -> dict:
    records = list_daily_records(start, end)
    nutrition = nutrition_summary(start, end)
    focus = focus_summary(start, end)
    sleep_values = [float(record["sleep_hours"]) for record in records if float(record["sleep_hours"] or 0) > 0]
    return {
        "average_score": _avg([record["daily_score"] for record in records]),
        "workout_hours": _sum(records, "workout_hours"),
        "study_hours": _sum(records, "study_hours"),
        "programming_hours": _sum(records, "programming_hours"),
        "reading_hours": _sum(records, "reading_hours"),
        "average_sleep": _avg(sleep_values),
        "total_steps": _sum(records, "steps"),
        "average_energy": _avg([record["energy"] for record in records]),
        "average_mood": _avg([record["mood"] for record in records]),
        "nutrition_average": nutrition["average_score"],
        "water_average": nutrition["average_water"],
        "focus_sessions": focus["sessions"],
        "focus_hours": focus["hours"],
    }


def _compare_metric(label: str, current: float, previous: float, *, lower_is_better: bool = False) -> dict:
    current_value = round(float(current or 0), 2)
    previous_value = round(float(previous or 0), 2)
    diff = round(current_value - previous_value, 2)
    percent = round((diff / previous_value) * 100, 1) if previous_value else (100 if current_value else 0)

    if abs(diff) < 0.01:
        status = "igual"
    elif lower_is_better:
        status = "melhorou" if diff < 0 else "piorou"
    else:
        status = "melhorou" if diff > 0 else "piorou"

    if label == "Sono medio" and current_value > 10:
        status = "atencao"

    return {
        "label": label,
        "current": current_value,
        "previous": previous_value,
        "diff": diff,
        "percent": percent,
        "status": status,
    }


def _parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _sum(records: list[dict], key: str) -> float:
    return round(sum(float(record.get(key) or 0) for record in records), 2)


def _avg(values) -> float:
    clean = [float(value or 0) for value in values if value is not None]
    if not clean:
        return 0
    return round(sum(clean) / len(clean), 2)
