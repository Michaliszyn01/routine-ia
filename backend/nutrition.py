from __future__ import annotations

from datetime import date, datetime, timedelta

from .database import get_connection
from .validators import (
    bool_to_int,
    bounded_float,
    bounded_int,
    sanitize_text,
    validate_date,
)


NUTRITION_COLUMNS = [
    "date",
    "breakfast_done",
    "lunch_done",
    "dinner_done",
    "healthy_snack_done",
    "water_liters",
    "protein_ok",
    "fruits_vegetables_ok",
    "ultra_processed_control",
    "meals_count",
    "nutrition_score",
    "observation",
]


def calculate_nutrition_score(data: dict) -> float:
    score = 0
    score += 10 if int(data.get("breakfast_done") or 0) else 0
    score += 15 if int(data.get("lunch_done") or 0) else 0
    score += 15 if int(data.get("dinner_done") or 0) else 0
    score += 10 if int(data.get("healthy_snack_done") or 0) else 0

    water = float(data.get("water_liters") or 0)
    if water >= 2:
        score += 20
    elif water >= 1:
        score += 10

    score += 15 if int(data.get("protein_ok") or 0) else 0
    score += 10 if int(data.get("fruits_vegetables_ok") or 0) else 0
    score += 5 if int(data.get("ultra_processed_control") or 0) else 0
    return float(min(score, 100))


def validate_nutrition_payload(payload: dict) -> dict:
    data = {
        "date": validate_date(payload.get("date")),
        "breakfast_done": bool_to_int(payload.get("breakfast_done")),
        "lunch_done": bool_to_int(payload.get("lunch_done")),
        "dinner_done": bool_to_int(payload.get("dinner_done")),
        "healthy_snack_done": bool_to_int(payload.get("healthy_snack_done")),
        "water_liters": bounded_float(payload.get("water_liters"), "water_liters", "Agua", maximum=20),
        "protein_ok": bool_to_int(payload.get("protein_ok")),
        "fruits_vegetables_ok": bool_to_int(payload.get("fruits_vegetables_ok")),
        "ultra_processed_control": bool_to_int(payload.get("ultra_processed_control")),
        "meals_count": bounded_int(payload.get("meals_count"), "meals_count", "Refeicoes", minimum=0, maximum=12),
        "observation": sanitize_text(payload.get("observation"), 2000),
    }
    data["nutrition_score"] = calculate_nutrition_score(data)
    return data


def get_nutrition_record(date_value: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM nutrition_records WHERE date = ?",
            (date_value,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def upsert_nutrition_record(payload: dict) -> dict:
    data = validate_nutrition_payload(payload)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO nutrition_records (
                date,
                breakfast_done,
                lunch_done,
                dinner_done,
                healthy_snack_done,
                water_liters,
                protein_ok,
                fruits_vegetables_ok,
                ultra_processed_control,
                meals_count,
                nutrition_score,
                observation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                breakfast_done = excluded.breakfast_done,
                lunch_done = excluded.lunch_done,
                dinner_done = excluded.dinner_done,
                healthy_snack_done = excluded.healthy_snack_done,
                water_liters = excluded.water_liters,
                protein_ok = excluded.protein_ok,
                fruits_vegetables_ok = excluded.fruits_vegetables_ok,
                ultra_processed_control = excluded.ultra_processed_control,
                meals_count = excluded.meals_count,
                nutrition_score = excluded.nutrition_score,
                observation = excluded.observation,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                data["date"],
                data["breakfast_done"],
                data["lunch_done"],
                data["dinner_done"],
                data["healthy_snack_done"],
                data["water_liters"],
                data["protein_ok"],
                data["fruits_vegetables_ok"],
                data["ultra_processed_control"],
                data["meals_count"],
                data["nutrition_score"],
                data["observation"],
            ),
        )
        row = conn.execute(
            "SELECT * FROM nutrition_records WHERE date = ?",
            (data["date"],),
        ).fetchone()
    return _row_to_dict(row)


def list_nutrition_records(start: str | None = None, end: str | None = None) -> list[dict]:
    query = "SELECT * FROM nutrition_records"
    params: list[str] = []
    clauses = []
    if start:
        clauses.append("date >= ?")
        params.append(start)
    if end:
        clauses.append("date <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY date DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def nutrition_summary(start: str | None = None, end: str | None = None) -> dict:
    records = list_nutrition_records(start, end)
    return {
        "record_count": len(records),
        "average_score": _avg([record["nutrition_score"] for record in records]),
        "average_water": _avg([record["water_liters"] for record in records]),
        "protein_days": _count(records, "protein_ok"),
        "fruits_vegetables_days": _count(records, "fruits_vegetables_ok"),
        "three_meals_days": sum(1 for record in records if int(record.get("meals_count") or 0) >= 3),
        "hydration_good_days": sum(1 for record in records if float(record.get("water_liters") or 0) >= 2),
        "good_nutrition_days": sum(1 for record in records if float(record.get("nutrition_score") or 0) >= 70),
    }


def weekly_nutrition_summary(reference_date: str | None = None) -> dict:
    start, end = _week_range(reference_date)
    summary = nutrition_summary(start, end)
    records = sorted(list_nutrition_records(start, end), key=lambda item: item["date"])
    labels = [_short_weekday((_parse_date(start) + timedelta(days=index)).weekday()) for index in range(7)]
    by_date = {record["date"]: record for record in records}
    score_by_day = []
    water_by_day = []
    for index in range(7):
        day = (_parse_date(start) + timedelta(days=index)).isoformat()
        record = by_date.get(day)
        score_by_day.append(float(record["nutrition_score"]) if record else 0)
        water_by_day.append(float(record["water_liters"]) if record else 0)

    summary.update(
        {
            "week_start": start,
            "week_end": end,
            "labels": labels,
            "score_by_day": score_by_day,
            "water_by_day": water_by_day,
            "insights": nutrition_insights(start, end),
        }
    )
    return summary


def nutrition_insights(start: str, end: str) -> list[str]:
    records = list_nutrition_records(start, end)
    if not records:
        return ["Registre alimentacao por alguns dias para revelar padroes de energia e consistencia."]

    summary = nutrition_summary(start, end)
    insights = [
        f"Sua nota alimentar media ficou em {summary['average_score']:.1f} nesta semana.",
        f"A hidratacao ficou boa em {summary['hydration_good_days']} dia(s) da semana.",
    ]

    if summary["average_score"] >= 75:
        insights.append("A base alimentar da semana ficou consistente, sem precisar transformar isso em contagem obsessiva.")
    elif summary["average_score"] < 55:
        insights.append("A alimentacao oscilou bastante; planejar refeicoes simples pode proteger energia e foco.")

    if summary["protein_days"] <= 2:
        insights.append("Proteina suficiente apareceu em poucos dias; isso pode influenciar recuperacao e saciedade.")

    weekend_records = [
        record for record in records if _parse_date(record["date"]).weekday() >= 5
    ]
    if weekend_records and _avg([record["nutrition_score"] for record in weekend_records]) < summary["average_score"] - 10:
        insights.append("A alimentacao caiu no fim de semana. Vale deixar uma opcao simples pronta para esses dias.")

    return insights


def nutrition_energy_correlation(start: str, end: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT n.date, n.nutrition_score, n.water_liters, d.energy
            FROM nutrition_records n
            JOIN daily_records d ON d.date = n.date
            WHERE n.date >= ? AND n.date <= ?
            ORDER BY n.date
            """,
            (start, end),
        ).fetchall()
    high = [row["energy"] for row in rows if float(row["nutrition_score"] or 0) >= 70]
    low = [row["energy"] for row in rows if float(row["nutrition_score"] or 0) < 70]
    return {
        "sample_size": len(rows),
        "energy_when_good": _avg(high),
        "energy_when_low": _avg(low),
        "message": _correlation_message(high, low),
    }


def _correlation_message(high: list[float], low: list[float]) -> str:
    if len(high) + len(low) < 3:
        return "Ainda faltam dados para comparar alimentacao e energia."
    high_avg = _avg(high)
    low_avg = _avg(low)
    if high_avg > low_avg + 0.4:
        return "Nos dias com alimentacao acima de 70, sua energia media foi maior."
    if low_avg > high_avg + 0.4:
        return "Sua energia nao subiu junto da alimentacao nesta amostra; sono e carga podem estar pesando."
    return "Alimentacao e energia ficaram relativamente estaveis nesta amostra."


def _week_range(reference_date: str | None = None) -> tuple[str, str]:
    current = _parse_date(reference_date or date.today().isoformat())
    start = current - timedelta(days=current.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _short_weekday(index: int) -> str:
    return ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"][index]


def _row_to_dict(row) -> dict:
    return dict(row)


def _avg(values) -> float:
    clean = [float(value or 0) for value in values if value is not None]
    if not clean:
        return 0
    return round(sum(clean) / len(clean), 2)


def _count(records: list[dict], key: str) -> int:
    return sum(1 for record in records if int(record.get(key) or 0))
