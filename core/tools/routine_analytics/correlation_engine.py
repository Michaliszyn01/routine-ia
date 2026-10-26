from __future__ import annotations

import math

from .analytics_schemas import MetricCorrelation


def summarize_metrics(rows: list[dict]) -> dict:
    rows_with_any_data = [row for row in rows if row.get("has_health_data") or row.get("has_pc_data") or row.get("has_daily_record")]
    trained = [row for row in rows if row.get("trained")]
    not_trained = [row for row in rows if not row.get("trained")]
    good_sleep = [row for row in rows if row.get("good_sleep")]
    short_sleep = [row for row in rows if row.get("short_sleep")]
    focus_good = [row for row in rows if row.get("focus_good")]
    combined_good = [
        row for row in rows
        if row.get("good_sleep") and row.get("trained") and row.get("focus_good")
    ]
    return {
        "days": len(rows),
        "days_with_any_data": len(rows_with_any_data),
        "average_sleep_hours": _avg([row["sleep_hours"] for row in rows if row.get("sleep_hours")]),
        "average_steps": round(_avg([row["steps"] for row in rows if row.get("steps")])),
        "average_productive_minutes": _avg([row["productive_minutes"] for row in rows if row.get("has_pc_data")]),
        "average_risk_minutes": _avg([row["risk_minutes"] for row in rows if row.get("has_pc_data")]),
        "average_routine_score": _avg([row["routine_score"] for row in rows if row.get("has_daily_record")]),
        "training_days": len(trained),
        "good_sleep_days": len(good_sleep),
        "short_sleep_days": len(short_sleep),
        "focus_good_days": len(focus_good),
        "combined_good_days": len(combined_good),
        "combined_good_dates": [row["date"] for row in combined_good],
        "trained_vs_not": _compare_groups(trained, not_trained),
        "good_sleep_vs_short_sleep": _compare_groups(good_sleep, short_sleep),
    }


def build_correlations(rows: list[dict]) -> list[dict]:
    pairs = [
        ("sleep_productive", "Sono x tempo produtivo", "sleep_hours", "productive_minutes"),
        ("sleep_risk", "Sono x apps de risco", "sleep_hours", "risk_minutes"),
        ("workout_productive", "Treino x tempo produtivo", "workout_minutes", "productive_minutes"),
        ("steps_productive", "Passos x tempo produtivo", "steps", "productive_minutes"),
        ("sleep_routine_score", "Sono x score diario", "sleep_hours", "routine_score"),
    ]
    result = []
    for key, label, left, right in pairs:
        values = [
            (float(row.get(left) or 0), float(row.get(right) or 0))
            for row in rows
            if float(row.get(left) or 0) > 0 and float(row.get(right) or 0) > 0
        ]
        value = _pearson(values)
        result.append(
            MetricCorrelation(
                key=key,
                label=label,
                value=value,
                strength=_strength(value, len(values)),
                direction=_direction(value),
                sample_size=len(values),
            ).__dict__
        )
    return result


def build_trends(rows: list[dict]) -> list[dict]:
    ordered = list(reversed(rows))
    if len(ordered) < 4:
        return []
    midpoint = len(ordered) // 2
    first = ordered[:midpoint]
    second = ordered[midpoint:]
    metrics = [
        ("sleep_hours", "Sono medio", "h"),
        ("productive_minutes", "Tempo produtivo", "min"),
        ("risk_minutes", "Apps de risco", "min"),
        ("routine_score", "Score diario", "pts"),
        ("steps", "Passos", ""),
    ]
    trends = []
    for key, label, unit in metrics:
        first_avg = _avg([row[key] for row in first if float(row.get(key) or 0) > 0])
        second_avg = _avg([row[key] for row in second if float(row.get(key) or 0) > 0])
        delta = round(second_avg - first_avg, 2)
        trends.append(
            {
                "key": key,
                "label": label,
                "first_half_average": first_avg,
                "second_half_average": second_avg,
                "delta": delta,
                "direction": "up" if delta > 0 else "down" if delta < 0 else "stable",
                "unit": unit,
            }
        )
    return trends


def _compare_groups(primary: list[dict], secondary: list[dict]) -> dict:
    return {
        "primary_days": len(primary),
        "secondary_days": len(secondary),
        "sleep_delta_hours": round(_avg([row["sleep_hours"] for row in primary if row.get("sleep_hours")]) - _avg([row["sleep_hours"] for row in secondary if row.get("sleep_hours")]), 2),
        "productive_delta_minutes": round(_avg([row["productive_minutes"] for row in primary if row.get("has_pc_data")]) - _avg([row["productive_minutes"] for row in secondary if row.get("has_pc_data")]), 1),
        "risk_delta_minutes": round(_avg([row["risk_minutes"] for row in primary if row.get("has_pc_data")]) - _avg([row["risk_minutes"] for row in secondary if row.get("has_pc_data")]), 1),
        "score_delta": round(_avg([row["routine_score"] for row in primary if row.get("has_daily_record")]) - _avg([row["routine_score"] for row in secondary if row.get("has_daily_record")]), 1),
    }


def _pearson(values: list[tuple[float, float]]) -> float:
    if len(values) < 3:
        return 0
    xs = [item[0] for item in values]
    ys = [item[1] for item in values]
    avg_x = sum(xs) / len(xs)
    avg_y = sum(ys) / len(ys)
    numerator = sum((x - avg_x) * (y - avg_y) for x, y in values)
    denominator_x = math.sqrt(sum((x - avg_x) ** 2 for x in xs))
    denominator_y = math.sqrt(sum((y - avg_y) ** 2 for y in ys))
    if not denominator_x or not denominator_y:
        return 0
    return round(numerator / (denominator_x * denominator_y), 2)


def _avg(values: list[float]) -> float:
    clean = [float(value or 0) for value in values]
    return round(sum(clean) / len(clean), 2) if clean else 0


def _strength(value: float, sample_size: int) -> str:
    if sample_size < 3:
        return "dados insuficientes"
    absolute = abs(value)
    if absolute >= 0.6:
        return "forte"
    if absolute >= 0.3:
        return "moderada"
    if absolute > 0:
        return "fraca"
    return "sem sinal"


def _direction(value: float) -> str:
    if value > 0:
        return "positiva"
    if value < 0:
        return "negativa"
    return "neutra"

