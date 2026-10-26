from __future__ import annotations

from .analytics_repository import combined_daily_rows, resolve_window
from .correlation_engine import build_correlations, build_trends, summarize_metrics
from .insight_rules import build_insights


def get_routine_analytics(period_days: int = 7, reference_date: str | None = None) -> dict:
    window = resolve_window(period_days, reference_date)
    rows = combined_daily_rows(window.period_days, window.end_date)
    summary = summarize_metrics(rows)
    correlations = build_correlations(rows)
    trends = build_trends(rows)
    insights = build_insights(rows, summary, correlations, trends)
    return {
        "ok": True,
        "period_days": window.period_days,
        "start_date": window.start_date,
        "end_date": window.end_date,
        "summary": summary,
        "daily": rows,
        "correlations": correlations,
        "trends": trends,
        "insights": insights,
        "safety_note": "Os dados sao pistas de rotina e bem-estar. O Routine IA nao faz diagnostico medico.",
    }

