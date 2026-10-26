from __future__ import annotations

from datetime import date, timedelta

from .focus_timer import focus_summary
from .life_os import bad_day_summary, habit_summary, life_goal_summary, study_summary
from .models import list_daily_records
from .nutrition import nutrition_summary
from .projects import hours_by_project
from .streaks import get_all_streaks


def get_evolution_summary(period: str = "month") -> dict:
    start, end, label = _period_range(period)
    records = sorted(list_daily_records(start, end), key=lambda item: item["date"])
    nutrition = nutrition_summary(start, end)
    focus = focus_summary(start, end)
    studies = study_summary(start, end)
    habits = habit_summary(start, end)
    goals = life_goal_summary(end)
    bad_days = bad_day_summary(start, end)
    streaks = get_all_streaks()
    project_hours = hours_by_project(start, end)
    weeks = _weekly_scores(records)

    score_values = [float(row.get("daily_score") or 0) for row in records]
    sleep_values = [float(row.get("sleep_hours") or 0) for row in records if float(row.get("sleep_hours") or 0) > 0]
    best_week = max(weeks, key=lambda item: item["average_score"], default=None)
    worst_week = min(weeks, key=lambda item: item["average_score"], default=None)

    return {
        "period": period,
        "label": label,
        "start": start,
        "end": end,
        "summary": {
            "best_week": best_week,
            "worst_week": worst_week,
            "longest_streak": streaks.get("main", {}).get("best_count", 0),
            "average_score": _avg(score_values),
            "study_hours": studies["total_hours"],
            "programming_hours": round(sum(float(row.get("programming_hours") or 0) for row in records), 2),
            "workouts": sum(1 for row in records if int(row.get("workout_done") or 0)),
            "average_sleep": _avg(sleep_values),
            "nutrition_average": nutrition.get("average_score", 0),
            "water_average": nutrition.get("average_water", 0),
            "focus_sessions": focus.get("sessions", 0),
            "focus_hours": focus.get("hours", 0),
            "habits_completed": habits.get("completed_this_week", 0),
            "life_goals_advanced": goals.get("active_count", 0),
            "bad_day_logs": bad_days.get("count", 0),
        },
        "charts": {
            "score_by_day": [{"date": row["date"], "value": float(row.get("daily_score") or 0)} for row in records],
            "hours_by_category": {
                "Estudo": studies["total_hours"],
                "Programacao": round(sum(float(row.get("programming_hours") or 0) for row in records), 2),
                "Treino": round(sum(float(row.get("workout_hours") or 0) for row in records), 2),
                "Foco": focus.get("hours", 0),
            },
            "nutrition": nutrition,
            "projects": project_hours,
            "studies_by_subject": studies["by_subject"],
            "habits": habits.get("habits", []),
        },
        "month_resume": _month_resume(records, studies, habits, goals),
    }


def _period_range(period: str) -> tuple[str, str, str]:
    today = date.today()
    normalized = (period or "month").lower()
    if normalized in {"previous_month", "mes_anterior"}:
        first = today.replace(day=1)
        last_previous = first - timedelta(days=1)
        start = last_previous.replace(day=1)
        end = last_previous
        return start.isoformat(), end.isoformat(), "Mes anterior"
    if normalized in {"last30", "last_30", "ultimos_30"}:
        return (today - timedelta(days=29)).isoformat(), today.isoformat(), "Ultimos 30 dias"
    if normalized in {"last90", "last_90", "ultimos_90"}:
        return (today - timedelta(days=89)).isoformat(), today.isoformat(), "Ultimos 90 dias"
    if normalized in {"year", "ano", "ano_atual"}:
        return today.replace(month=1, day=1).isoformat(), today.isoformat(), "Ano atual"
    start = today.replace(day=1)
    return start.isoformat(), today.isoformat(), "Mes atual"


def _weekly_scores(records: list[dict]) -> list[dict]:
    buckets: dict[str, list[float]] = {}
    for row in records:
        current = date.fromisoformat(row["date"])
        start = current - timedelta(days=current.weekday())
        buckets.setdefault(start.isoformat(), []).append(float(row.get("daily_score") or 0))
    return [{"week_start": key, "average_score": _avg(values)} for key, values in sorted(buckets.items())]


def _month_resume(records: list[dict], studies: dict, habits: dict, goals: dict) -> str:
    if not records:
        return "Ainda ha poucos dados para resumir o periodo."
    return (
        f"Periodo com {len(records)} dia(s) registrados, media {_avg([row.get('daily_score') for row in records]):.1f}, "
        f"{studies['total_hours']:.1f}h de estudos e {habits.get('completed_this_week', 0)} habitos concluidos. "
        f"Objetivos ativos: {goals.get('active_count', 0)}."
    )


def _avg(values) -> float:
    clean = [float(value or 0) for value in values if value is not None]
    return round(sum(clean) / len(clean), 2) if clean else 0
