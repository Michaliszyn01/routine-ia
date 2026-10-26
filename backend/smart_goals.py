from __future__ import annotations

from datetime import date, timedelta

from .models import get_goals_by_category, list_daily_records, update_goal
from .nutrition import nutrition_summary


CATEGORY_FIELDS = {
    "workout": "workout_hours",
    "study": "study_hours",
    "programming": "programming_hours",
    "reading": "reading_hours",
}


def generate_smart_goal_suggestions() -> list[dict]:
    goals = get_goals_by_category()
    weeks = _last_weeks(4)
    suggestions = []

    nutrition_recent = nutrition_summary(weeks[-1]["start"], weeks[-1]["end"]) if weeks else {}
    latest_records = list_daily_records(weeks[-1]["start"], weeks[-1]["end"]) if weeks else []
    average_sleep = _avg([record["sleep_hours"] for record in latest_records if float(record.get("sleep_hours") or 0) > 0])
    average_energy = _avg([record["energy"] for record in latest_records])

    if average_sleep and average_sleep < 6.5:
        suggestions.append(
            _suggestion(
                "sleep",
                "Sono medio baixo",
                "Priorize regularidade de sono antes de aumentar metas de carga.",
                "Melhor base de energia e recuperacao.",
                "daily_hours_goal",
                min(8, float(goals.get("sleep", {}).get("daily_hours_goal") or 8)),
            )
        )

    if nutrition_recent and nutrition_recent.get("average_score", 0) < 60:
        suggestions.append(
            _suggestion(
                "nutrition",
                "Alimentacao e hidratacao ainda instaveis",
                "Mantenha metas de rotina estaveis e foque em agua, refeicoes base e proteina suficiente.",
                "Menos oscilacao de energia durante a semana.",
                None,
                None,
            )
        )

    for category, field in CATEGORY_FIELDS.items():
        goal = goals.get(category)
        if not goal:
            continue
        weekly_goal = float(goal.get("weekly_hours_goal") or 0)
        if weekly_goal <= 0:
            continue
        totals = [_sum(list_daily_records(week["start"], week["end"]), field) for week in weeks[-3:]]
        if len(totals) < 3:
            continue
        if all(total >= weekly_goal for total in totals):
            next_goal = round(weekly_goal * 1.1, 2)
            suggestions.append(
                _suggestion(
                    category,
                    f"{_label(category)} bateu a meta por 3 semanas",
                    f"Subir levemente a meta semanal de {weekly_goal:g}h para {next_goal:g}h.",
                    "Crescimento pequeno sem mudar a arquitetura da rotina.",
                    "weekly_hours_goal",
                    next_goal,
                )
            )
        elif all(total < weekly_goal * 0.55 for total in totals):
            next_goal = round(max(0.5, weekly_goal * 0.75), 2)
            suggestions.append(
                _suggestion(
                    category,
                    f"{_label(category)} ficou abaixo por 3 semanas",
                    f"Reduzir temporariamente a meta para {next_goal:g}h e reconstruir consistencia.",
                    "Menos friccao e maior chance de voltar a registrar progresso.",
                    "weekly_hours_goal",
                    next_goal,
                )
            )

    if average_energy and average_energy < 3:
        suggestions.append(
            _suggestion(
                "recovery",
                "Energia media baixa",
                "Evite aumentar treino ou programacao nesta semana; prefira blocos menores e recuperacao.",
                "Protege constancia sem empurrar carga agressiva.",
                None,
                None,
            )
        )

    if not suggestions:
        suggestions.append(
            _suggestion(
                "general",
                "Metas parecem estaveis",
                "Mantenha as metas atuais por mais uma semana e observe sono, energia e alimentacao.",
                "Mais dados antes de alterar a direcao.",
                None,
                None,
            )
        )
    return suggestions[:8]


def apply_suggestion(payload: dict) -> dict:
    category = payload.get("category")
    field = payload.get("field")
    value = payload.get("value")
    if not category or not field:
        return {"applied": False, "message": "Sugestao informativa, sem alteracao automatica."}

    goals = get_goals_by_category()
    goal = goals.get(category)
    if not goal:
        return {"applied": False, "message": "Categoria sem meta editavel."}

    updated_payload = dict(goal)
    updated_payload[field] = value
    updated = update_goal(category, updated_payload)
    return {"applied": True, "goal": updated}


def _last_weeks(count: int) -> list[dict]:
    today = date.today()
    current_start = today - timedelta(days=today.weekday())
    weeks = []
    for offset in range(count - 1, -1, -1):
        start = current_start - timedelta(days=offset * 7)
        end = start + timedelta(days=6)
        weeks.append({"start": start.isoformat(), "end": end.isoformat()})
    return weeks


def _suggestion(category, diagnosis, suggestion, impact, field, value) -> dict:
    return {
        "id": f"{category}:{field or 'info'}:{value or 'none'}",
        "category": category,
        "diagnosis": diagnosis,
        "suggestion": suggestion,
        "impact": impact,
        "field": field,
        "value": value,
        "applicable": bool(field),
    }


def _label(category: str) -> str:
    return {
        "workout": "Treino",
        "study": "Estudo",
        "programming": "Programacao",
        "reading": "Leitura",
        "sleep": "Sono",
    }.get(category, category)


def _sum(records: list[dict], key: str) -> float:
    return round(sum(float(record.get(key) or 0) for record in records), 2)


def _avg(values) -> float:
    clean = [float(value or 0) for value in values if value is not None]
    if not clean:
        return 0
    return round(sum(clean) / len(clean), 2)
