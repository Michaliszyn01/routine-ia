from __future__ import annotations

from datetime import date

from .models import get_goals_by_category, list_daily_records


def _generate_weekly_report_mvp(week_start, week_end):
    records = list_daily_records(week_start, week_end)
    goals = get_goals_by_category()
    insights = []

    sleep_values = [float(record["sleep_hours"]) for record in records if record["sleep_hours"] > 0]
    average_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0
    average_score = (
        sum(float(record["daily_score"]) for record in records) / len(records)
        if records
        else 0
    )
    programming_total = sum(float(record["programming_hours"]) for record in records)
    workout_total = sum(float(record["workout_hours"]) for record in records)
    reading_total = sum(float(record["reading_hours"]) for record in records)
    average_energy = (
        sum(float(record["energy"]) for record in records) / len(records)
        if records
        else 0
    )
    average_mood = (
        sum(float(record["mood"]) for record in records) / len(records)
        if records
        else 0
    )
    best_day = max(records, key=lambda record: float(record["daily_score"]), default=None)

    if average_score >= 80:
        insights.append("Semana muito consistente. Você manteve uma boa base de rotina.")
    elif average_score >= 60:
        insights.append("Semana boa, mas ainda existe espaço para melhorar consistência.")
    elif records:
        insights.append("Semana instável. Vale revisar metas e reduzir fricção na rotina.")

    if average_sleep and average_sleep < 7:
        insights.append(
            "Sono abaixo do ideal. Isso pode afetar energia, humor e foco."
        )
    elif average_sleep >= 8:
        insights.append("Seu sono ficou em uma faixa forte para recuperação e energia.")

    programming_goal = float(goals.get("programming", {}).get("weekly_hours_goal") or 0)
    if programming_goal and programming_total < programming_goal:
        insights.append(
            "Programação ficou abaixo da meta semanal. Tente reservar blocos menores e mais constantes."
        )
    elif programming_goal and programming_total >= programming_goal:
        insights.append("Sua meta semanal de programação foi alcançada.")

    workout_goal = float(goals.get("workout", {}).get("weekly_hours_goal") or 0)
    if workout_goal and workout_total >= workout_goal:
        insights.append("Boa consistência no treino.")

    reading_goal = float(goals.get("reading", {}).get("weekly_hours_goal") or 0)
    if reading_goal and reading_total >= reading_goal:
        insights.append("Leitura ficou dentro da meta semanal.")

    if average_energy and average_energy < 3:
        insights.append("Sua energia media ficou baixa. Talvez seja melhor reduzir metas temporariamente.")

    if average_mood and average_mood < 3:
        insights.append("Humor medio baixo nesta semana. Observe sono, carga e recuperacao.")

    if best_day:
        insights.append(
            f"Seu melhor dia foi {best_day['weekday']} ({best_day['date']}). Observe o que funcionou nesse dia."
        )

    if not insights:
        insights.append("Ainda há poucos dados nesta semana. Registre mais dias para melhorar o resumo.")

    return {
        "period": {"week_start": week_start, "week_end": week_end},
        "engine": "rules-placeholder",
        "metrics": {
            "average_score": round(average_score, 1),
            "average_sleep": round(average_sleep, 1),
            "programming_total": round(programming_total, 1),
            "workout_total": round(workout_total, 1),
            "reading_total": round(reading_total, 1),
            "average_energy": round(average_energy, 1),
            "average_mood": round(average_mood, 1),
        },
        "insights": insights,
    }


def _generate_weekly_ai_report_mvp(week_start, week_end):
    # Future AI integration point: call OpenAI or another model here using the
    # rule-based report as structured context, then return the same response shape.
    return generate_weekly_report(week_start, week_end)


# V2 report engine. The staged implementations keep old behavior available
# without relying on silent function shadowing.
from .database import get_connection as _get_connection_v2
from .focus_timer import focus_summary as _focus_summary_v2
from .insights import get_week_comparison as _get_week_comparison_v2
from .nutrition import (
    list_nutrition_records as _list_nutrition_records_v2,
    nutrition_energy_correlation as _nutrition_energy_correlation_v2,
    nutrition_summary as _nutrition_summary_v2,
)
from .projects import hours_by_project as _hours_by_project_v2


def _generate_weekly_report_core_v2(week_start, week_end):
    records = sorted(list_daily_records(week_start, week_end), key=lambda item: item["date"])
    goals = get_goals_by_category()
    nutrition = _nutrition_summary_v2(week_start, week_end)
    nutrition_records = _list_nutrition_records_v2(week_start, week_end)
    focus = _focus_summary_v2(week_start, week_end)
    project_hours = _hours_by_project_v2(week_start, week_end)
    comparison = _get_week_comparison_v2(week_start)
    insights = []

    sleep_values = [float(record["sleep_hours"]) for record in records if record["sleep_hours"] > 0]
    average_sleep = _avg_v2(sleep_values)
    average_score = _avg_v2([record["daily_score"] for record in records])
    programming_total = _sum_v2(records, "programming_hours")
    study_total = _sum_v2(records, "study_hours")
    workout_total = _sum_v2(records, "workout_hours")
    reading_total = _sum_v2(records, "reading_hours")
    average_energy = _avg_v2([record["energy"] for record in records])
    average_mood = _avg_v2([record["mood"] for record in records])
    best_day = max(records, key=lambda record: float(record["daily_score"]), default=None)
    worst_day = min(records, key=lambda record: float(record["daily_score"]), default=None)

    if not records:
        insights.append("Ainda nao ha registros de rotina nesta semana. A tela Hoje e o caminho mais rapido para criar a primeira base.")
    elif average_score >= 80:
        insights.append("Semana muito consistente. A pontuacao media ficou forte sem indicar necessidade de metas agressivas.")
    elif average_score >= 60:
        insights.append("Semana boa, com espaco para ganhar regularidade nos pontos que mais oscilaram.")
    else:
        insights.append("Semana instavel. Antes de subir metas, vale reduzir friccao e proteger sono, agua e blocos curtos.")

    if best_day:
        insights.append(_day_sentence_v2("melhor", best_day, nutrition_records))
    if worst_day and worst_day != best_day:
        insights.append(_day_sentence_v2("pior", worst_day, nutrition_records))

    score_trend = comparison["metrics"].get("average_score", {})
    if score_trend.get("status") == "melhorou":
        insights.append(f"Pontuacao media subiu {abs(score_trend.get('percent', 0)):.1f}% em relacao a semana anterior.")
    elif score_trend.get("status") == "piorou":
        insights.append(f"Pontuacao media caiu {abs(score_trend.get('percent', 0)):.1f}% frente a semana anterior; observe sono, alimentacao e foco.")

    programming_goal = float(goals.get("programming", {}).get("weekly_hours_goal") or 0)
    if programming_goal and programming_total < programming_goal:
        gap = programming_goal - programming_total
        insights.append(f"Programacao ficou {gap:.1f}h abaixo da meta semanal. Blocos de 25 a 50 minutos podem recuperar ritmo sem pesar.")
    elif programming_goal and programming_total >= programming_goal:
        insights.append("Programacao atingiu a meta semanal; se a energia ficou boa, a meta pode ser mantida ou subir pouco.")

    study_goal = float(goals.get("study", {}).get("weekly_hours_goal") or 0)
    if study_goal and study_total >= study_goal and average_energy >= 3.5:
        insights.append("Estudo ficou acima da meta com energia aceitavel. Isso sugere boa janela para manter a cadencia.")

    workout_goal = float(goals.get("workout", {}).get("weekly_hours_goal") or 0)
    if workout_goal and workout_total >= workout_goal and average_energy < 3:
        insights.append("Treino bateu a meta, mas a energia ficou baixa. Pode ser sinal para olhar recuperacao antes de aumentar carga.")

    if average_sleep and average_sleep < 7:
        insights.append("Sono medio abaixo de 7h pode estar limitando energia, humor e foco.")
    elif 7 <= average_sleep <= 9:
        insights.append("Sono ficou em uma faixa favoravel para recuperacao e consistencia.")
    elif average_sleep > 10:
        insights.append("Sono medio acima de 10h merece atencao: mais horas nem sempre significam melhor recuperacao.")

    if nutrition["record_count"]:
        insights.append(f"Alimentacao: media {nutrition['average_score']:.1f}, agua media {nutrition['average_water']:.1f}L e hidratacao boa em {nutrition['hydration_good_days']} dia(s).")
        insights.append(_nutrition_energy_correlation_v2(week_start, week_end)["message"])

    if focus["sessions"]:
        insights.append(f"Foco: {focus['sessions']} sessao(oes) concluidas, somando {focus['hours']:.1f}h.")
    else:
        insights.append("Nenhum bloco de foco concluido foi registrado; um timer curto pode facilitar a retomada.")

    if project_hours:
        top_name, top_hours = next(iter(project_hours.items()))
        insights.append(f"Projeto com mais tempo: {top_name}, com {top_hours:.1f}h na semana.")

    report_text = "\n".join(insights)
    _persist_weekly_report_v2(week_start, week_end, report_text, average_score, nutrition["average_score"])

    return {
        "period": {"week_start": week_start, "week_end": week_end},
        "engine": "rules-v2",
        "metrics": {
            "average_score": round(average_score, 1),
            "average_sleep": round(average_sleep, 1),
            "programming_total": round(programming_total, 1),
            "study_total": round(study_total, 1),
            "workout_total": round(workout_total, 1),
            "reading_total": round(reading_total, 1),
            "average_energy": round(average_energy, 1),
            "average_mood": round(average_mood, 1),
            "nutrition_average": round(nutrition["average_score"], 1),
            "water_average": round(nutrition["average_water"], 1),
            "focus_sessions": focus["sessions"],
            "focus_hours": focus["hours"],
            "project_hours": project_hours,
        },
        "best_day": best_day,
        "worst_day": worst_day,
        "nutrition": nutrition,
        "focus": focus,
        "project_hours": project_hours,
        "comparison": comparison,
        "insights": insights,
        "report_text": report_text,
    }


def generate_weekly_ai_report_placeholder(week_start, week_end):
    report = _generate_weekly_report_core_v2(week_start, week_end)
    report["engine"] = "rules-v2-ai-placeholder"
    report["ai_ready"] = True
    return report


def _generate_weekly_ai_report_v2(week_start, week_end):
    return generate_weekly_ai_report_placeholder(week_start, week_end)


def _day_sentence_v2(kind: str, record: dict, nutrition_records: list[dict]) -> str:
    nutrition_by_date = {item["date"]: item for item in nutrition_records}
    nutrition = nutrition_by_date.get(record["date"])
    parts = [
        f"{record['sleep_hours']:.1f}h sono",
        f"{record['study_hours']:.1f}h estudo",
        f"{record['programming_hours']:.1f}h programacao",
    ]
    if nutrition:
        parts.append(f"alimentacao {nutrition['nutrition_score']:.0f}")
        parts.append(f"agua {nutrition['water_liters']:.1f}L")
    label = "melhor" if kind == "melhor" else "pior"
    return f"Seu {label} dia foi {record['weekday']} ({record['date']}), com {record['daily_score']:.1f} pontos: " + ", ".join(parts) + "."


def _persist_weekly_report_v2(week_start: str, week_end: str, text: str, average_score: float, nutrition_average: float) -> None:
    with _get_connection_v2() as conn:
        conn.execute(
            """
            INSERT INTO weekly_reports (
                week_start, week_end, report_text, score_average, nutrition_average
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(week_start, week_end) DO UPDATE SET
                report_text = excluded.report_text,
                score_average = excluded.score_average,
                nutrition_average = excluded.nutrition_average,
                updated_at = CURRENT_TIMESTAMP
            """,
            (week_start, week_end, text, average_score, nutrition_average),
        )


def _sum_v2(records: list[dict], key: str) -> float:
    return round(sum(float(record.get(key) or 0) for record in records), 2)


def _avg_v2(values) -> float:
    clean = [float(value or 0) for value in values if value is not None]
    if not clean:
        return 0
    return round(sum(clean) / len(clean), 2)

# V3 report enrichment: the weekly report stays deterministic and local, but
# now includes the new Life OS modules as context.
_generate_weekly_report_v2 = _generate_weekly_report_core_v2


def _generate_weekly_report_life_os(week_start, week_end):
    report = _generate_weekly_report_v2(week_start, week_end)
    from .alerts import get_alerts
    from .life_os import bad_day_summary, get_weekly_planner, get_weekly_review, habit_summary, life_goal_summary, study_summary
    from .load_balance import get_load_balance
    from .patterns import detect_patterns

    life_goals = life_goal_summary(week_end)
    planner = get_weekly_planner(week_start)
    review = get_weekly_review(week_start)
    patterns = detect_patterns(week_start, week_end)
    alerts = get_alerts(week_end)
    habits = habit_summary(week_start, week_end)
    studies = study_summary(week_start, week_end)
    load = get_load_balance(week_start)
    bad_days = bad_day_summary(week_start, week_end)

    report["metrics"].update(
        {
            "life_goals_active": life_goals["active_count"],
            "life_goals_average_progress": life_goals["average_progress"],
            "planner_items": len(planner.get("items") or planner.get("suggestion", {}).get("items", [])),
            "habits_completed": habits["completed_this_week"],
            "study_session_hours": studies["total_hours"],
            "study_accuracy": studies["accuracy"],
            "load_index": load["index"],
            "bad_day_count": bad_days["count"],
            "active_alerts": alerts["count"],
            "patterns_count": len(patterns.get("patterns", [])),
        }
    )
    if life_goals["main_goal"]:
        report["insights"].append(f"Objetivo principal: {life_goals['main_goal']['title']} ({life_goals['main_goal']['progress_percent']:.0f}% de progresso).")
    if planner.get("plan"):
        done = sum(1 for item in planner.get("items", []) if int(item.get("completed") or 0))
        report["insights"].append(f"Planejamento semanal: {done}/{len(planner.get('items', []))} item(ns) concluidos.")
    else:
        report["insights"].append("Planejamento semanal ainda nao foi salvo; gere uma sugestao editavel para a proxima semana.")
    if review.get("review"):
        report["insights"].append(f"Revisao semanal registrada. Vitoria: {review['review'].get('main_win') or 'sem destaque preenchido'}.")
    else:
        report["insights"].append("Revisao semanal ainda pendente; ela ajuda o relatorio a ficar menos generico.")
    for pattern in patterns.get("patterns", [])[:2]:
        report["insights"].append(f"Padrao detectado: {pattern['title']} - {pattern['suggestion']}")
    if alerts["count"]:
        first_alert = alerts["alerts"][0]
        report["insights"].append(f"Alerta importante: {first_alert['title']} - {first_alert['message']}")
    report["insights"].append(f"Habitos: {habits['completed_this_week']} conclusao(oes) na semana; estudos por sessoes: {studies['total_hours']:.1f}h com {studies['accuracy']:.1f}% de acerto.")
    report["insights"].append(f"Carga da semana: {load['level']} ({load['index']}/100). {load['suggestion']}")
    if bad_days["count"]:
        report["insights"].append(f"Modo Dia Ruim usado {bad_days['count']} vez(es), mantendo continuidade sem exigir dia perfeito.")

    report["life_goals"] = life_goals
    report["planner"] = planner
    report["weekly_review"] = review
    report["patterns"] = patterns
    report["alerts"] = alerts
    report["habits"] = habits
    report["studies"] = studies
    report["load_balance"] = load
    report["bad_days"] = bad_days
    report["report_text"] = "\n".join(report["insights"])
    return report


def _generate_weekly_ai_report_v3(week_start, week_end):
    report = _generate_weekly_report_life_os(week_start, week_end)
    report["engine"] = "rules-v3-ai-ready"
    report["ai_ready"] = True
    return report

# V4 report enrichment for local PC usage. This is intentionally local-only:
# it reads the level 1 daily monitoring table and does not call any service.
_generate_weekly_report_v3 = _generate_weekly_report_life_os


def generate_weekly_report(week_start, week_end):
    report = _generate_weekly_report_v3(week_start, week_end)
    from core.tools.monitoring.monitoring_repository import range_summary

    usage = range_summary(week_start, week_end)
    report["metrics"].update(
        {
            "pc_total_minutes": usage["total_minutes"],
            "pc_productive_minutes": usage["productive_minutes"],
            "pc_neutral_minutes": usage["neutral_minutes"],
            "pc_distraction_minutes": usage["distraction_minutes"],
        }
    )
    if usage["total_seconds"]:
        top_app = usage.get("top_app") or {}
        top_category = usage.get("top_category") or {}
        report["insights"].append(f"Uso do PC: {usage['total_minutes']:.0f}min monitorados na semana, com {usage['productive_minutes']:.0f}min produtivos e {usage['distraction_minutes']:.0f}min de distracao.")
        if top_app:
            report["insights"].append(f"App mais usado: {top_app['label']} ({top_app['minutes']:.0f}min).")
        if top_category:
            report["insights"].append(f"Categoria mais usada no PC: {top_category['label']} ({top_category['minutes']:.0f}min).")
        project = next((item for item in usage["by_category"] if item["label"] == "Projeto"), None)
        if project:
            report["insights"].append(f"Projetos detectados por uso de apps: {project['minutes']:.0f}min em aplicativos ligados a trabalho/codigo.")
        if usage["distraction_minutes"] >= 180:
            report["insights"].append("Apps classificados como risco passaram de 3h na semana. Se isso estiver atrapalhando suas metas, revise horarios de uso.")
        _append_app_usage_context(report, usage, week_start, week_end)
    else:
        report["insights"].append("Uso do PC ainda nao tem dados nesta semana. O monitoramento fica desligado ate voce ativar.")
    _append_phase2_context(report, week_start, week_end)
    report["app_usage"] = usage
    report["report_text"] = "\n".join(report["insights"])
    return report


def generate_weekly_ai_report(week_start, week_end):
    report = generate_weekly_report(week_start, week_end)
    report["engine"] = "rules-v4-ai-ready"
    report["ai_ready"] = True
    return report


def _append_phase2_context(report: dict, week_start: str, week_end: str) -> None:
    from .adhd_support import phase2_summary
    from .checklists import checklist_summary
    from .microtasks import microtask_summary

    phase2 = phase2_summary(week_start, week_end)
    microtasks = microtask_summary(week_start, week_end)
    checklists = checklist_summary(week_start, week_end)
    report["metrics"].update(
        {
            "minimum_saved_days": phase2["minimum_days"],
            "cant_start_uses": phase2["cant_start_uses"],
            "microtasks_completed": microtasks["completed"],
            "microtasks_total": microtasks["total"],
            "checklists_used": checklists["count"],
            "command_center_completions": phase2["command_completions"],
            "minimum_energy_average": phase2["minimum_energy_average"],
        }
    )
    if phase2["minimum_days"]:
        report["insights"].append(
            f"Voce salvou {phase2['minimum_days']} dia(s) no minimo nesta semana. Isso ajudou a manter continuidade mesmo em dias dificeis."
        )
    if phase2["cant_start_uses"]:
        report["insights"].append(
            f"O fluxo 'nao consigo comecar' foi usado {phase2['cant_start_uses']} vez(es), reduzindo a barreira de inicio."
        )
    if microtasks["completed"]:
        report["insights"].append(
            f"Microtarefas concluidas: {microtasks['completed']}/{microtasks['total']}. Pequenos passos tambem contam."
        )
    if checklists["count"]:
        report["insights"].append(
            f"Checklists usados {checklists['count']} vez(es), ajudando a diminuir decisao antes da acao."
        )
    report["adhd_first"] = {"phase2": phase2, "microtasks": microtasks, "checklists": checklists}


def _append_app_usage_context(report: dict, usage: dict, week_start: str, week_end: str) -> None:
    productive_by_day: dict[str, int] = {}
    for item in usage.get("by_day") or []:
        day = item.get("label")
        seconds = int(item.get("seconds") or 0)
        if day:
            productive_by_day[day] = productive_by_day.get(day, 0) + seconds

    records = list_daily_records(week_start, week_end)
    productive_scores = [
        float(record.get("daily_score") or 0)
        for record in records
        if productive_by_day.get(record.get("date"), 0) >= 30 * 60
    ]
    other_scores = [
        float(record.get("daily_score") or 0)
        for record in records
        if productive_by_day.get(record.get("date"), 0) < 30 * 60
    ]
    if productive_scores and other_scores:
        diff = _avg_v2(productive_scores) - _avg_v2(other_scores)
        if abs(diff) >= 5:
            direction = "maior" if diff > 0 else "menor"
            report["insights"].append(f"Nos dias com pelo menos 30min produtivos no PC, a pontuacao diaria ficou {abs(diff):.1f} pontos {direction}.")

    focus = _focus_summary_v2(week_start, week_end)
    focus_dates = set((focus.get("by_date") or {}).keys())
    if focus_dates:
        focus_productive = _avg_v2([productive_by_day.get(day, 0) / 60 for day in focus_dates])
        no_focus_days = [record["date"] for record in records if record["date"] not in focus_dates]
        no_focus_productive = _avg_v2([productive_by_day.get(day, 0) / 60 for day in no_focus_days])
        if focus_productive > no_focus_productive + 15:
            report["insights"].append("Seu tempo produtivo no PC foi maior nos dias em que usou o timer de foco.")

    weekend_distraction = 0
    weekday_distraction = 0
    distraction_by_day: dict[str, int] = {}
    for item in usage.get("by_day_category") or []:
        if item.get("label") in {"Risco", "Distracao"}:
            day = item.get("date")
            if day:
                distraction_by_day[day] = distraction_by_day.get(day, 0) + int(item.get("seconds") or 0)
    for day, seconds in distraction_by_day.items():
        try:
            is_weekend = date.fromisoformat(day).weekday() >= 5
        except ValueError:
            is_weekend = False
        if is_weekend:
            weekend_distraction += seconds
        else:
            weekday_distraction += seconds
    if weekend_distraction >= 45 * 60 and weekend_distraction > weekday_distraction:
        report["insights"].append("O tempo em apps de entretenimento/distração aumentou no fim de semana.")
