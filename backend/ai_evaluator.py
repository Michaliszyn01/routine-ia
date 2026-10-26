from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date
from typing import Any

from backend import models
from core.tools.day_planner.planner_service import get_today_plan
from core.tools.focus_mode.focus_service import get_focus_summary_today
from core.tools.monitoring.monitoring_repository import daily_summary
from core.tools.weekly_review.weekly_service import range_weekly_review


NOTICE = "Avaliacao de rotina: use como pista pratica, nao como diagnostico medico."


def evaluate_day(target_date: str | None = None) -> dict:
    date_value = str(target_date or models.today_iso())[:10]
    context = _day_context(date_value)
    return _evaluate("day", context, _fallback_day(context))


def evaluate_week(start: str | None = None, end: str | None = None) -> dict:
    if not start or not end:
        start, end = models.week_range()
    context = _week_context(str(start)[:10], str(end)[:10])
    return _evaluate("week", context, _fallback_week(context))


def _evaluate(period_type: str, context: dict, fallback_text: str) -> dict:
    settings = models.get_settings()
    model = settings.get("ai_evaluation_model") or "gemma3:4b"
    enabled = str(settings.get("ai_evaluation_enabled", "true")).lower() == "true"
    if not enabled:
        return _payload(period_type, context, fallback_text, model, "disabled", "Avaliacao IA desativada nas configuracoes.")

    try:
        text = _call_ollama(
            settings.get("ai_evaluation_url") or "http://127.0.0.1:11434",
            model,
            _prompt(period_type, context),
            _int(settings.get("ai_evaluation_timeout_seconds"), 8),
        )
    except Exception as exc:
        return _payload(period_type, context, fallback_text, model, "local-fallback", str(exc))

    if not text:
        return _payload(period_type, context, fallback_text, model, "local-fallback", "O modelo retornou vazio.")
    return _payload(period_type, context, text, model, "gemma", "")


def _payload(period_type: str, context: dict, evaluation: str, model: str, source: str, error: str) -> dict:
    return {
        "ok": True,
        "period_type": period_type,
        "source": source,
        "model": model,
        "date": context.get("date"),
        "week_start": context.get("week_start"),
        "week_end": context.get("week_end"),
        "evaluation": evaluation.strip(),
        "notice": NOTICE,
        "error": error,
    }


def _day_context(date_value: str) -> dict:
    today = models.get_today_bundle(date_value)
    focus = get_focus_summary_today(date_value)
    usage = daily_summary(date_value)
    planner = get_today_plan(date_value)
    daily = today.get("daily") or {}
    nutrition = today.get("nutrition") or {}
    summary = {
        "score": daily.get("daily_score", 0),
        "sleep_hours": daily.get("sleep_hours", 0),
        "energy": daily.get("energy", 0),
        "mood": daily.get("mood", 0),
        "study_hours": daily.get("study_hours", 0),
        "programming_hours": daily.get("programming_hours", 0),
        "reading_hours": daily.get("reading_hours", 0),
        "workout_hours": daily.get("workout_hours", 0),
        "steps": daily.get("steps", 0),
        "water_liters": nutrition.get("water_liters", 0),
        "nutrition_score": nutrition.get("nutrition_score", nutrition.get("score", 0)),
        "focus_minutes": round((focus.get("summary", {}).get("focused_seconds") or 0) / 60, 1),
        "distracted_minutes": round((focus.get("summary", {}).get("distracted_seconds") or 0) / 60, 1),
        "pc_productive_minutes": usage.get("productive_minutes", 0),
        "pc_risk_minutes": usage.get("risk_minutes", 0),
        "plan_status": (planner.get("plan") or {}).get("status", "sem plano"),
        "next_step": (planner.get("next_step") or {}).get("title", ""),
    }
    return {
        "date": date_value,
        "weekday": today.get("weekday"),
        "summary": summary,
        "observations": {
            "routine": daily.get("observation", ""),
            "nutrition": nutrition.get("observation", ""),
        },
        "top_focus_breakers": focus.get("top_focus_breakers", [])[:4],
        "top_apps": usage.get("by_app", [])[:5],
    }


def _week_context(start: str, end: str) -> dict:
    review = range_weekly_review(start, end, label="Avaliacao IA")
    context = dict(review.get("context") or {})
    context.update(
        {
            "week_start": start,
            "week_end": end,
            "enough_data": review.get("enough_data"),
            "message": review.get("message"),
            "insights": review.get("insights", [])[:6],
            "suggestions": review.get("suggestions", [])[:6],
        }
    )
    return context


def _prompt(period_type: str, context: dict) -> str:
    label = "do dia" if period_type == "day" else "da semana"
    return (
        "Voce e o avaliador de rotina do Routine IA. "
        "Use apenas os dados em JSON. Nao invente numeros, nao faca diagnostico medico "
        "e nao recomende remedios ou tratamento. Escreva em portugues do Brasil, curto e pratico.\n"
        f"Faca uma avaliacao {label} em 4 partes com titulos: Leitura, Padrao, Ajuste, Proximo passo.\n"
        "Cada parte deve ter no maximo 2 frases. Seja acolhedor, direto e sem bronca.\n"
        f"DADOS:\n{json.dumps(_compact(context), ensure_ascii=False, sort_keys=True)}"
    )


def _call_ollama(base_url: str, model: str, prompt: str, timeout_seconds: int) -> str:
    url = base_url.rstrip("/") + "/api/generate"
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 360},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError("Ollama indisponivel ou modelo Gemma nao carregado.") from exc
    except TimeoutError as exc:
        raise RuntimeError("Timeout ao chamar o Gemma local.") from exc
    return str(data.get("response") or "").strip()


def _fallback_day(context: dict) -> str:
    summary = context.get("summary", {})
    score = _float(summary.get("score"))
    sleep = _float(summary.get("sleep_hours"))
    focus = _float(summary.get("focus_minutes"))
    risk = _float(summary.get("pc_risk_minutes"))
    main = "dia com poucos dados registrados"
    if score >= 75:
        main = "dia bem consistente"
    elif score >= 50:
        main = "dia mediano, com base para ajustar"
    elif score > 0:
        main = "dia mais pesado ou irregular"
    adjustment = "registre o minimo do dia e escolha um passo pequeno para manter continuidade"
    if sleep and sleep < 6.5:
        adjustment = "proteja o sono hoje antes de aumentar a carga"
    elif risk > focus and risk >= 30:
        adjustment = "reduza um app de risco e comece por um bloco curto"
    return (
        f"Leitura: Foi um {main}. Score {score:g}, sono {sleep:g}h e foco registrado de {focus:g} min.\n"
        f"Padrao: Apps de risco somaram {risk:g} min; use isso como pista de ambiente, nao como culpa.\n"
        f"Ajuste: {adjustment}.\n"
        "Proximo passo: abra uma tarefa de 5 minutos e salve uma observacao curta depois."
    )


def _fallback_week(context: dict) -> str:
    summary = context.get("summary", {})
    score = _float(summary.get("average_score"))
    focus_hours = _float(summary.get("focus_real_hours"))
    risk_hours = _float(summary.get("risk_hours"))
    completed = int(_float(summary.get("blocks_completed")))
    suggestion = "planeje menos blocos e deixe o primeiro passo bem pequeno"
    if focus_hours >= 3:
        suggestion = "repita os blocos que mais deram foco real"
    elif risk_hours > focus_hours:
        suggestion = "coloque barreira simples nos apps que mais quebraram foco"
    return (
        f"Leitura: A semana fechou com score medio {score:g} e {focus_hours:g}h de foco real.\n"
        f"Padrao: Foram {risk_hours:g}h em apps de risco e {completed} blocos concluidos.\n"
        f"Ajuste: {suggestion}.\n"
        "Proximo passo: escolha uma prioridade da semana e transforme em um bloco curto para segunda."
    )


def _compact(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return ""
    if isinstance(value, dict):
        return {str(key): _compact(item, depth + 1) for key, item in list(value.items())[:24]}
    if isinstance(value, list):
        return [_compact(item, depth + 1) for item in value[:8]]
    if isinstance(value, str):
        return value[:500]
    return value


def _float(value) -> float:
    try:
        return round(float(value or 0), 1)
    except (TypeError, ValueError):
        return 0


def _int(value, default: int) -> int:
    try:
        return max(1, min(int(float(value or default)), 30))
    except (TypeError, ValueError):
        return default
