from __future__ import annotations


def build_insights(rows: list[dict], summary: dict, correlations: list[dict], trends: list[dict]) -> list[dict]:
    insights: list[dict] = []
    if summary.get("days_with_any_data", 0) < 3:
        return [
            {
                "level": "info",
                "title": "Poucos dados ainda",
                "message": "Registre alguns dias de rotina, saude e uso do PC para as pistas ficarem mais uteis.",
            }
        ]

    trained_delta = summary.get("trained_vs_not", {})
    if trained_delta.get("primary_days", 0) >= 2 and trained_delta.get("productive_delta_minutes", 0) > 10:
        insights.append(
            {
                "level": "positive",
                "title": "Treino e produtividade aparecem juntos",
                "message": "Nos dias com treino, seu tempo produtivo ficou maior neste periodo.",
            }
        )
    if trained_delta.get("primary_days", 0) >= 2 and trained_delta.get("sleep_delta_hours", 0) > 0.4:
        insights.append(
            {
                "level": "info",
                "title": "Sono melhor em dias com treino",
                "message": "Os dias com treino tiveram mais sono em media. Use isso apenas como pista de rotina.",
            }
        )

    sleep_risk = next((item for item in correlations if item["key"] == "sleep_risk"), {})
    if sleep_risk.get("sample_size", 0) >= 3 and sleep_risk.get("value", 0) < -0.3:
        insights.append(
            {
                "level": "warning",
                "title": "Sono menor pode acompanhar mais risco",
                "message": "Neste recorte, menos sono apareceu junto de mais tempo em apps de risco.",
            }
        )

    sleep_focus = next((item for item in correlations if item["key"] == "sleep_productive"), {})
    if sleep_focus.get("sample_size", 0) >= 3 and sleep_focus.get("value", 0) > 0.3:
        insights.append(
            {
                "level": "positive",
                "title": "Sono e foco caminham juntos",
                "message": "Mais sono apareceu junto de mais tempo produtivo neste periodo.",
            }
        )

    if summary.get("combined_good_days", 0):
        dates = ", ".join(summary.get("combined_good_dates", [])[:3])
        insights.append(
            {
                "level": "positive",
                "title": "Dias combinados bons",
                "message": f"{summary['combined_good_days']} dia(s) combinaram sono bom, treino e foco. Primeiros: {dates}.",
            }
        )

    risk_trend = next((item for item in trends if item["key"] == "risk_minutes"), {})
    if risk_trend.get("delta", 0) > 15:
        insights.append(
            {
                "level": "warning",
                "title": "Apps de risco subiram",
                "message": "A segunda metade do periodo teve mais minutos em apps de risco.",
            }
        )

    if not insights:
        insights.append(
            {
                "level": "info",
                "title": "Padroes ainda discretos",
                "message": "Ja existe um resumo combinado, mas os sinais ainda estao fracos ou com poucos dados.",
            }
        )
    return insights[:6]

