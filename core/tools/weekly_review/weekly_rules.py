from __future__ import annotations


PUNITIVE_WORDS = ["falhou", "improdutivo", "desperdicou", "fracasso"]


def best_day(days: list[dict]) -> dict | None:
    if not days:
        return None
    return max(days, key=lambda item: item.get("day_score", 0))


def hard_day(days: list[dict]) -> dict | None:
    if not days:
        return None
    return min(days, key=lambda item: item.get("day_score", 0))


def build_insights(days: list[dict], focus_summary: dict, health_summary: dict, plan_summary: dict) -> list[str]:
    insights: list[str] = []
    if len(days) < 3:
        insights.append("Ainda ha poucos dados para padroes confiaveis.")
    good_sleep_days = [day for day in days if day.get("sleep_hours", 0) >= 7]
    if good_sleep_days and plan_summary.get("completion_rate", 0) > 0:
        insights.append("Nos seus dados recentes, parece que dias com sono acima de 7h tiveram mais espaco para concluir blocos.")
    if focus_summary.get("focused_seconds", 0) > focus_summary.get("distracted_seconds", 0):
        insights.append("Esta semana mostrou mais tempo dentro do bloco do que fora dele nas sessoes registradas.")
    if health_summary.get("workouts_done", 0) >= 2:
        insights.append("Pode existir uma tendencia de mais consistencia nos dias com treino registrado.")
    if plan_summary.get("skipped_blocks", 0) > plan_summary.get("completed_blocks", 0):
        insights.append("Os blocos podem estar grandes demais para alguns dias; blocos menores podem reduzir atrito.")
    if focus_summary.get("sessions", 0) == 0:
        insights.append("Ainda nao ha sessoes de foco suficientes para avaliar padroes de execucao.")
    return _clean_language(insights[:5])


def build_suggestions(days: list[dict], focus_summary: dict, health_summary: dict, plan_summary: dict) -> list[str]:
    suggestions: list[str] = []
    if focus_summary.get("top_focus_type"):
        suggestions.append(f"Colocar {focus_summary['top_focus_type']} no horario em que voce mais conseguiu focar.")
    if health_summary.get("avg_sleep_seconds", 0) and health_summary["avg_sleep_seconds"] < 7 * 3600:
        suggestions.append("Usar blocos menores nos dias apos sono ruim.")
    if plan_summary.get("completion_rate", 0) < 60:
        suggestions.append("Comecar o dia com uma tarefa pequena para destravar.")
    if focus_summary.get("distracted_seconds", 0) > 30 * 60:
        suggestions.append("Separar um bloco curto de retomada quando o tempo fora do bloco aumentar.")
    if health_summary.get("workouts_done", 0):
        suggestions.append("Manter treino nos dias em que a rotina fica mais estavel.")
    if not suggestions:
        suggestions.append("Manter a semana simples: um bloco essencial por dia ja cria continuidade.")
    return _clean_language(suggestions[:5])


def _clean_language(items: list[str]) -> list[str]:
    clean: list[str] = []
    for item in items:
        text = item
        for word in PUNITIVE_WORDS:
            text = text.replace(word, "ajustou")
        clean.append(text)
    return clean
