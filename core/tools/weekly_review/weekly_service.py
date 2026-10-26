from __future__ import annotations

from datetime import date, timedelta

from . import weekly_repository as repo
from .weekly_rules import best_day, build_insights, build_suggestions, hard_day
from .weekly_schemas import ReviewWindow


def current_week_review() -> dict:
    return range_weekly_review(*_week_range(date.today()), label="Semana atual")


def previous_week_review() -> dict:
    start, _ = _week_range(date.today())
    previous = start - timedelta(days=7)
    return range_weekly_review(previous.isoformat(), (previous + timedelta(days=6)).isoformat(), label="Semana anterior")


def range_weekly_review(start: str, end: str | None = None, label: str = "Periodo") -> dict:
    if end is None:
        start_date, end_date = _week_range(_parse_date(start))
        start, end = start_date.isoformat(), end_date.isoformat()
    window = ReviewWindow(str(start)[:10], str(end)[:10], label)
    daily = repo.daily_records(window.start_date, window.end_date)
    nutrition = repo.nutrition_records(window.start_date, window.end_date)
    health = _health_summary(repo.health_data(window.start_date, window.end_date), daily)
    focus = repo.focus_data(window.start_date, window.end_date)
    monitoring = repo.monitoring_data(window.start_date, window.end_date)
    plan = _plan_summary(repo.plan_data(window.start_date, window.end_date))
    days = _day_scores(daily, health, focus, monitoring, plan)
    best = best_day(days)
    hard = hard_day(days)
    summary = _summary(daily, health, focus, monitoring, plan)
    action_summary = _action_summary(daily, nutrition)
    insights = build_insights(days, focus, health, plan)
    suggestions = build_suggestions(days, focus, health, plan)
    enough_data = len(days) >= 3 or focus.get("sessions", 0) >= 3 or plan.get("planned_blocks", 0) >= 5

    return {
        "ok": True,
        "period": {"start_date": window.start_date, "end_date": window.end_date, "label": window.label},
        "week_start": window.start_date,
        "week_end": window.end_date,
        "summary": summary,
        "action_summary": action_summary,
        "best_day": best,
        "hard_day": hard,
        "focus_summary": focus,
        "health_summary": health,
        "plan_summary": plan,
        "productivity_summary": monitoring,
        "top_focus_breakers": repo.focus_breakers(window.start_date, window.end_date) or _monitoring_breakers(monitoring),
        "insights": insights,
        "suggestions": suggestions,
        "review": repo.saved_review(window.start_date, window.end_date),
        "enough_data": enough_data,
        "message": "Boa consistencia nessa semana." if enough_data else "Ainda ha poucos dados para uma revisao confiavel. Continue usando o app por mais alguns dias.",
        "context": {
            "summary": summary,
            "action_summary": action_summary,
            "focus": focus,
            "health": health,
            "plan": plan,
            "monitoring": monitoring,
            "best_day": best,
            "hard_day": hard,
            "top_focus_breakers": repo.focus_breakers(window.start_date, window.end_date),
        },
    }


def _summary(daily: list[dict], health: dict, focus: dict, monitoring: dict, plan: dict) -> dict:
    scores = [float(row.get("daily_score") or 0) for row in daily]
    return {
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "focus_real_seconds": int(focus.get("focused_seconds") or 0),
        "focus_real_hours": round(int(focus.get("focused_seconds") or 0) / 3600, 2),
        "pc_productive_seconds": int(monitoring.get("productive_seconds") or 0),
        "pc_productive_hours": round(int(monitoring.get("productive_seconds") or 0) / 3600, 2),
        "risk_seconds": int(monitoring.get("risk_seconds") or 0),
        "risk_hours": round(int(monitoring.get("risk_seconds") or 0) / 3600, 2),
        "avg_sleep_seconds": int(health.get("avg_sleep_seconds") or 0),
        "avg_sleep_hours": round(int(health.get("avg_sleep_seconds") or 0) / 3600, 2),
        "steps_total": int(health.get("steps_total") or 0),
        "workouts_done": int(health.get("workouts_done") or 0),
        "blocks_completed": int(plan.get("completed_blocks") or 0),
        "blocks_skipped": int(plan.get("skipped_blocks") or 0),
    }


def _action_summary(daily: list[dict], nutrition: list[dict]) -> dict:
    nutrition_by_date = {row["date"]: row for row in nutrition}
    enem_days = 0
    three_key_days = 0
    game_before_study_days = 0
    days_without_decent_meal = 0
    total_game_hours = 0.0

    for row in daily:
        date_value = row["date"]
        food = nutrition_by_date.get(date_value, {})
        enem_done = bool(int(row.get("study_done") or 0)) or float(row.get("study_hours") or 0) > 0
        body_done = bool(int(row.get("workout_done") or 0))
        decent_meal = bool(int(food.get("dinner_done") or 0)) or bool(int(food.get("healthy_snack_done") or 0))
        game_hours = float(row.get("game_hours") or 0)

        enem_days += int(enem_done)
        three_key_days += int(enem_done and body_done and decent_meal)
        game_before_study_days += int(game_hours > 0 and not enem_done)
        days_without_decent_meal += int(not decent_meal)
        total_game_hours += game_hours

    recorded_days = len(daily)
    average_game_hours = round(total_game_hours / recorded_days, 2) if recorded_days else 0
    main_alert = _main_action_alert(
        recorded_days,
        enem_days,
        three_key_days,
        game_before_study_days,
        days_without_decent_meal,
        average_game_hours,
    )
    return {
        "recorded_days": recorded_days,
        "enem_days": enem_days,
        "three_key_days": three_key_days,
        "game_before_study_days": game_before_study_days,
        "average_game_hours": average_game_hours,
        "days_without_decent_meal": days_without_decent_meal,
        "main_alert": main_alert,
        "next_week_rule": _next_week_rule(main_alert),
    }


def _main_action_alert(
    recorded_days: int,
    enem_days: int,
    three_key_days: int,
    game_before_study_days: int,
    days_without_decent_meal: int,
    average_game_hours: float,
) -> str:
    if recorded_days == 0:
        return "Sem dados suficientes: registre pelo menos um dia."
    if game_before_study_days:
        return "Jogo apareceu antes do ENEM em dia registrado."
    if three_key_days < max(1, recorded_days // 2):
        return "As 3 chaves ainda nao viraram base da semana."
    if days_without_decent_meal >= max(2, recorded_days // 2):
        return "Refeicao decente alem do almoco falhou em muitos dias."
    if average_game_hours > 2:
        return "Tempo medio de jogo passou de 2h por dia."
    if enem_days < max(1, recorded_days // 2):
        return "ENEM apareceu pouco na semana."
    return "Padrao principal: manter o minimo antes de buscar mais."


def _next_week_rule(alert: str) -> str:
    if "Jogo apareceu" in alert:
        return "Jogo so abre depois das 3 chaves e depois de 19:30."
    if "3 chaves" in alert:
        return "Antes de qualquer extra, fechar ENEM, corpo e refeicao."
    if "Refeicao" in alert:
        return "Escolher uma refeicao decente simples antes do horario de jogo."
    if "2h" in alert:
        return "Definir limite de jogo antes de abrir qualquer jogo."
    if "ENEM" in alert:
        return "Primeiro bloco do dia e sempre ENEM de 25 minutos."
    return "Repetir a regra: vencer o proximo bloco, nao o dia inteiro."


def _health_summary(raw: dict, daily: list[dict]) -> dict:
    sleep_by_day = {row["date"]: int(row["total_sleep_seconds"] or 0) for row in raw["sleep"]}
    manual_sleep = {row["date"]: int(float(row["sleep_hours_auto"] or 0) * 3600) for row in raw["manual"] if float(row["sleep_hours_auto"] or 0) > 0}
    daily_sleep = {row["date"]: int(float(row.get("sleep_hours") or 0) * 3600) for row in daily if float(row.get("sleep_hours") or 0) > 0}
    sleep_by_day = {**daily_sleep, **manual_sleep, **sleep_by_day}
    step_by_day = {row["date"]: int(row["total_steps"] or 0) for row in raw["steps"]}
    for row in raw["manual"]:
        if int(row["steps_auto"] or 0):
            step_by_day[row["date"]] = int(row["steps_auto"] or 0)
    sleep_values = [value for value in sleep_by_day.values() if value > 0]
    steps_values = [value for value in step_by_day.values() if value > 0]
    workout_seconds = sum(int(row["active_seconds"] or row["elapsed_seconds"] or 0) for row in raw["workouts"])
    manual_workouts = sum(int(float(row["workout_minutes_auto"] or 0) * 60) for row in raw["manual"])
    heart_values = [int(row["avg_bpm"] or 0) for row in raw["heart"] if int(row["avg_bpm"] or 0) > 0]
    return {
        "avg_sleep_seconds": round(sum(sleep_values) / len(sleep_values)) if sleep_values else 0,
        "best_sleep_day": _max_pair(sleep_by_day),
        "worst_sleep_day": _min_pair(sleep_by_day),
        "steps_total": sum(steps_values),
        "avg_steps": round(sum(steps_values) / len(steps_values)) if steps_values else 0,
        "workouts_done": len(raw["workouts"]) + sum(1 for row in raw["manual"] if float(row["workout_minutes_auto"] or 0) > 0),
        "workout_seconds": workout_seconds + manual_workouts,
        "avg_bpm": round(sum(heart_values) / len(heart_values)) if heart_values else 0,
        "has_data": bool(sleep_values or steps_values or raw["workouts"] or heart_values),
        "notice": "Dados de saude sao pistas de rotina, nao diagnostico medico.",
    }


def _plan_summary(blocks: list[dict]) -> dict:
    status_counts: dict[str, int] = {}
    type_done: dict[str, int] = {}
    type_skipped: dict[str, int] = {}
    for block in blocks:
        status = block.get("status") or "pending"
        kind = block.get("type") or "task"
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "done":
            type_done[kind] = type_done.get(kind, 0) + 1
        if status == "skipped":
            type_skipped[kind] = type_skipped.get(kind, 0) + 1
    total = len(blocks)
    completed = status_counts.get("done", 0)
    return {
        "planned_blocks": total,
        "completed_blocks": completed,
        "skipped_blocks": status_counts.get("skipped", 0),
        "rescheduled_blocks": status_counts.get("rescheduled", 0),
        "completion_rate": round((completed / total) * 100, 1) if total else 0,
        "top_completed_type": _top_key(type_done),
        "top_skipped_type": _top_key(type_skipped),
    }


def _day_scores(daily: list[dict], health: dict, focus: dict, monitoring: dict, plan: dict) -> list[dict]:
    focus_by_date = {item["date"]: int(item.get("focused_seconds") or 0) for item in focus.get("sessions_list", [])}
    monitoring_by_day = {item["label"]: item["seconds"] for item in monitoring.get("by_day", [])}
    days: list[dict] = []
    for row in daily:
        sleep = float(row.get("sleep_hours") or 0)
        score = float(row.get("daily_score") or 0)
        focus_bonus = min(focus_by_date.get(row["date"], 0) / 1800, 10)
        day_score = score + focus_bonus + (8 if sleep >= 7 else 0)
        days.append(
            {
                "date": row["date"],
                "weekday": row.get("weekday") or "",
                "score": score,
                "sleep_hours": sleep,
                "focused_seconds": focus_by_date.get(row["date"], 0),
                "risk_seconds": monitoring_by_day.get(row["date"], 0),
                "day_score": round(day_score, 1),
                "reason": _day_reason(sleep, focus_by_date.get(row["date"], 0), score),
            }
        )
    return days


def _day_reason(sleep_hours: float, focused_seconds: int, score: float) -> str:
    parts = []
    if sleep_hours >= 7:
        parts.append("sono bom")
    if focused_seconds:
        parts.append(f"{round(focused_seconds / 3600, 1)}h de foco")
    if score >= 70:
        parts.append("score consistente")
    return " + ".join(parts) if parts else "dia com menos dados registrados"


def _monitoring_breakers(monitoring: dict) -> list[dict]:
    return [
        item
        for item in monitoring.get("by_app", [])
        if item.get("category") in {"Risco", "Distracao", "Lazer"}
    ][:6]


def _week_range(reference: date) -> tuple[date, date]:
    start = reference - timedelta(days=reference.weekday())
    return start, start + timedelta(days=6)


def _parse_date(value: str | None) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return date.today()


def _max_pair(values: dict[str, int]) -> dict | None:
    if not values:
        return None
    key = max(values, key=values.get)
    return {"date": key, "seconds": values[key]}


def _min_pair(values: dict[str, int]) -> dict | None:
    clean = {key: value for key, value in values.items() if value > 0}
    if not clean:
        return None
    key = min(clean, key=clean.get)
    return {"date": key, "seconds": clean[key]}


def _top_key(values: dict[str, int]) -> str:
    return max(values.items(), key=lambda item: item[1])[0] if values else ""
