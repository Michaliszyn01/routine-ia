from __future__ import annotations

from datetime import date, timedelta

from .database import get_connection
from .models import list_daily_records
from .nutrition import list_nutrition_records


def detect_patterns(start_date: str | None = None, end_date: str | None = None) -> dict:
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.fromisoformat(end_date) - timedelta(days=29)).isoformat()
    records = sorted(list_daily_records(start_date, end_date), key=lambda item: item["date"])
    if len(records) < 7:
        return {
            "patterns": [],
            "message": "Ainda nao ha dados suficientes para detectar padroes confiaveis.",
            "minimum_days": 7,
            "recorded_days": len(records),
        }

    nutrition = {row["date"]: row for row in list_nutrition_records(start_date, end_date)}
    focus_dates = _focus_dates(start_date, end_date)
    patterns: list[dict] = []

    _compare_groups(
        patterns,
        "Sono baixo x pontuacao baixa",
        [row for row in records if float(row["sleep_hours"] or 0) and float(row["sleep_hours"] or 0) < 7],
        [row for row in records if float(row["sleep_hours"] or 0) >= 7],
        "daily_score",
        "alerta",
        "Quando o sono fica abaixo de 7h, a pontuacao tende a cair.",
        "Proteja o horario de dormir antes de aumentar metas.",
    )
    _compare_groups(
        patterns,
        "Sono bom x energia alta",
        [row for row in records if float(row["sleep_hours"] or 0) >= 7],
        [row for row in records if float(row["sleep_hours"] or 0) and float(row["sleep_hours"] or 0) < 7],
        "energy",
        "positivo",
        "Dias com sono suficiente aparecem com energia melhor.",
        "Mantenha uma janela minima de sono nos dias de estudo e treino.",
    )
    nutrition_rows = [dict(row, **{"daily_score": _record(records, row["date"], "daily_score"), "energy": _record(records, row["date"], "energy"), "mood": _record(records, row["date"], "mood")}) for row in nutrition.values()]
    _compare_groups(
        patterns,
        "Alimentacao boa x energia alta",
        [row for row in nutrition_rows if float(row.get("nutrition_score") or 0) >= 70],
        [row for row in nutrition_rows if float(row.get("nutrition_score") or 0) < 70],
        "energy",
        "positivo",
        "Dias com alimentacao mais consistente tendem a sustentar melhor energia.",
        "Use alimentacao simples e hidratacao como base dos dias mais exigentes.",
    )
    _compare_groups(
        patterns,
        "Hidratacao baixa x humor baixo",
        [row for row in nutrition_rows if float(row.get("water_liters") or 0) < 2],
        [row for row in nutrition_rows if float(row.get("water_liters") or 0) >= 2],
        "mood",
        "alerta",
        "Menos agua apareceu junto de humor mais baixo.",
        "Deixe uma garrafa visivel e registre agua na tela Hoje.",
    )
    _compare_groups(
        patterns,
        "Timer de foco x maior pontuacao",
        [row for row in records if row["date"] in focus_dates],
        [row for row in records if row["date"] not in focus_dates],
        "daily_score",
        "positivo",
        "Dias com sessao de foco concluida tendem a render mais.",
        "Use blocos de 25 a 50 minutos para iniciar o dia produtivo.",
    )
    _compare_groups(
        patterns,
        "Foco em projetos x programacao",
        [row for row in records if row["date"] in focus_dates],
        [row for row in records if row["date"] not in focus_dates],
        "programming_hours",
        "positivo",
        "Dias com foco concluido tambem aparecem com mais horas de programacao.",
        "Vincule sessoes de foco aos projetos principais para transformar foco em progresso visivel.",
    )
    _compare_groups(
        patterns,
        "Programacao baixa em dias de treino pesado",
        [row for row in records if float(row.get("workout_hours") or 0) >= 1],
        [row for row in records if float(row.get("workout_hours") or 0) < 1],
        "programming_hours",
        "alerta",
        "Dias com treino mais pesado parecem reduzir a programacao registrada.",
        "Em dias de treino, use blocos menores de programacao ou planeje programar antes do treino.",
        inverse=True,
    )
    next_sleep_rows = _rows_with_next_sleep(records)
    _compare_groups(
        patterns,
        "Treino x sono do dia seguinte",
        [row for row in next_sleep_rows if float(row.get("workout_hours") or 0) > 0 or int(row.get("workout_done") or 0)],
        [row for row in next_sleep_rows if not (float(row.get("workout_hours") or 0) > 0 or int(row.get("workout_done") or 0))],
        "sleep_next",
        "neutro",
        "Treino e sono do dia seguinte mostraram diferenca perceptivel nesta amostra.",
        "Observe horario e intensidade do treino para ajustar recuperacao.",
    )
    _compare_groups(
        patterns,
        "Cafe da manha x energia",
        [row for row in nutrition_rows if int(row.get("breakfast_done") or 0)],
        [row for row in nutrition_rows if not int(row.get("breakfast_done") or 0)],
        "energy",
        "positivo",
        "Dias com cafe da manha registrado aparecem com energia diferente.",
        "Se isso se repetir, planeje uma primeira refeicao simples nos dias de estudo e foco.",
    )
    weekend = [row for row in records if date.fromisoformat(row["date"]).weekday() >= 5]
    weekdays = [row for row in records if date.fromisoformat(row["date"]).weekday() < 5]
    _compare_groups(
        patterns,
        "Fim de semana com queda de rotina",
        weekend,
        weekdays,
        "daily_score",
        "alerta",
        "Fins de semana parecem menos consistentes que dias uteis.",
        "Planeje uma rotina minima para sabado e domingo.",
        inverse=True,
    )

    if not patterns:
        return {
            "patterns": [],
            "message": "Nenhum padrao forte apareceu ainda. Continue registrando para melhorar a confianca.",
            "minimum_days": 7,
            "recorded_days": len(records),
        }
    return {"patterns": patterns, "message": "", "minimum_days": 7, "recorded_days": len(records)}


def _compare_groups(patterns, title, primary, baseline, key, pattern_type, description, suggestion, inverse: bool = False):
    if len(primary) < 3 or len(baseline) < 3:
        return
    primary_avg = _avg([row.get(key) for row in primary])
    baseline_avg = _avg([row.get(key) for row in baseline])
    diff = primary_avg - baseline_avg
    threshold = _threshold_for(key)
    enough = diff <= -threshold if inverse else abs(diff) >= threshold
    if not enough:
        return
    confidence = min(95, 45 + (len(primary) + len(baseline)) * 3 + int(abs(diff) * (8 if threshold < 2 else 1.4)))
    impact = "alto" if abs(diff) >= threshold * 1.8 else "medio"
    patterns.append({
        "title": title,
        "description": description,
        "confidence": confidence,
        "impact": impact,
        "suggestion": suggestion,
        "type": pattern_type,
        "evidence": {"sample": len(primary) + len(baseline), "difference": round(diff, 2)},
    })


def _threshold_for(key: str) -> float:
    if key in {"energy", "mood"}:
        return 0.6
    if key in {"programming_hours", "study_hours", "workout_hours", "reading_hours", "sleep_next"}:
        return 0.45
    return 8


def _rows_with_next_sleep(records: list[dict]) -> list[dict]:
    by_date = {row["date"]: row for row in records}
    enriched = []
    for row in records:
        next_date = (date.fromisoformat(row["date"]) + timedelta(days=1)).isoformat()
        next_row = by_date.get(next_date)
        if not next_row or not float(next_row.get("sleep_hours") or 0):
            continue
        item = dict(row)
        item["sleep_next"] = float(next_row.get("sleep_hours") or 0)
        enriched.append(item)
    return enriched


def _focus_dates(start_date: str, end_date: str) -> set[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM focus_sessions WHERE completed = 1 AND date >= ? AND date <= ?",
            (start_date, end_date),
        ).fetchall()
    return {row["date"] for row in rows}


def _record(records: list[dict], date_value: str, key: str) -> float:
    for row in records:
        if row["date"] == date_value:
            return float(row.get(key) or 0)
    return 0


def _avg(values) -> float:
    clean = [float(value or 0) for value in values if value is not None]
    return round(sum(clean) / len(clean), 2) if clean else 0
