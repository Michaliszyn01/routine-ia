from __future__ import annotations

from .focus_timer import focus_summary
from .life_os import study_summary, week_range
from .models import history_summary, list_daily_records
from .nutrition import nutrition_summary


def get_load_balance(reference_date: str | None = None) -> dict:
    start, end = week_range(reference_date)
    records = list_daily_records(start, end)
    history = history_summary(start, end)
    nutrition = nutrition_summary(start, end)
    focus = focus_summary(start, end)
    studies = study_summary(start, end)

    activity_hours = (
        float(history.get("total_study_hours") or 0)
        + float(history.get("total_programming_hours") or 0)
        + float(history.get("total_workout_hours") or 0)
        + float(focus.get("hours") or 0) * 0.35
        + float(studies.get("total_hours") or 0) * 0.6
    )
    high_score_days = sum(1 for row in records if float(row.get("daily_score") or 0) >= 75)
    rest_days = 7 - sum(1 for row in records if float(row.get("workout_hours") or 0) + float(row.get("study_hours") or 0) + float(row.get("programming_hours") or 0) >= 1)
    avg_sleep = float(history.get("average_sleep") or 0)
    avg_energy = float(history.get("average_energy") or 0)
    avg_mood = float(history.get("average_mood") or 0)
    nutrition_score = float(nutrition.get("average_score") or 0)

    load = min(100, activity_hours * 4.2 + high_score_days * 3 - max(rest_days - 2, 0) * 2)
    recovery_penalty = 0
    if avg_sleep and avg_sleep < 7:
        recovery_penalty += 12
    if avg_energy and avg_energy < 3:
        recovery_penalty += 10
    if avg_mood and avg_mood < 3:
        recovery_penalty += 6
    if nutrition.get("record_count") and nutrition_score < 55:
        recovery_penalty += 6
    index = int(max(0, min(100, load + recovery_penalty)))
    level = _level(index)

    if index >= 70 and (avg_sleep and avg_sleep < 7 or avg_energy and avg_energy < 3):
        explanation = "Sua semana parece pesada demais para sua recuperacao atual."
        suggestion = "Reduza uma meta por 48h, proteja sono e mantenha apenas blocos essenciais."
    elif index >= 70:
        explanation = "Carga alta, mas aparentemente bem sustentada."
        suggestion = "Mantenha recuperacao visivel: agua, sono e pausa curta apos blocos longos."
    elif index < 40 and (float(history.get("total_study_hours") or 0) + float(history.get("total_programming_hours") or 0)) < 3:
        explanation = "Semana leve, mas talvez pouco produtiva."
        suggestion = "Escolha um bloco de estudo ou projeto pequeno para recuperar tracao."
    else:
        explanation = "Carga equilibrada para os dados registrados."
        suggestion = "Continue ajustando pela energia real, nao apenas por volume de atividade."

    return {
        "week_start": start,
        "week_end": end,
        "index": index,
        "level": level,
        "explanation": explanation,
        "suggestion": suggestion,
        "inputs": {
            "activity_hours": round(activity_hours, 1),
            "average_sleep": avg_sleep,
            "average_energy": avg_energy,
            "average_mood": avg_mood,
            "nutrition_score": nutrition_score,
            "high_score_days": high_score_days,
            "rest_days": rest_days,
        },
    }


def _level(index: int) -> str:
    if index <= 39:
        return "leve"
    if index <= 69:
        return "equilibrada"
    if index <= 84:
        return "pesada"
    return "excessiva"
