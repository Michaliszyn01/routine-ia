from __future__ import annotations

from datetime import date, timedelta

from .app_rules import score_for_label


TABLE_NAME = "monitoring_app_usage_daily"


def add_usage_seconds(app_name: str, label: str, seconds: int, target_date: str | None = None) -> dict:
    from backend.database import get_connection

    date_value = target_date or date.today().isoformat()
    clean_app = (app_name or "Desconhecido").strip() or "Desconhecido"
    clean_label = (label or "Neutro").strip() or "Neutro"
    amount = max(0, int(seconds or 0))
    with get_connection() as conn:
        conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (date, app_name, label, total_seconds, created_at, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(date, app_name) DO UPDATE SET
                label = excluded.label,
                total_seconds = {TABLE_NAME}.total_seconds + excluded.total_seconds,
                updated_at = CURRENT_TIMESTAMP
            """,
            (date_value, clean_app, clean_label, amount),
        )
        row = conn.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE date = ? AND app_name = ?",
            (date_value, clean_app),
        ).fetchone()
    return dict(row)


def save_increments(increments: list[dict], target_date: str | None = None) -> list[dict]:
    return [
        add_usage_seconds(item["app_name"], item["label"], int(item["seconds"]), target_date)
        for item in increments
        if int(item.get("seconds") or 0) > 0
    ]


def daily_summary(target_date: str | None = None) -> dict:
    date_value = target_date or date.today().isoformat()
    return range_summary(date_value, date_value)


def weekly_summary(reference_date: str | None = None) -> dict:
    ref = date.fromisoformat(reference_date) if reference_date else date.today()
    start = ref - timedelta(days=ref.weekday())
    end = start + timedelta(days=6)
    return range_summary(start.isoformat(), end.isoformat())


def range_summary(start_date: str, end_date: str) -> dict:
    from backend.database import get_connection

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT date, app_name, label, total_seconds
            FROM {TABLE_NAME}
            WHERE date >= ? AND date <= ?
            ORDER BY total_seconds DESC, app_name ASC
            """,
            (start_date, end_date),
        ).fetchall()
    records = [dict(row) for row in rows]
    by_app = [
        {
            "label": app_name,
            "app_name": app_name,
            "category": values["label"],
            "seconds": values["seconds"],
            "minutes": round(values["seconds"] / 60, 1),
        }
        for app_name, values in _group_apps(records)
    ]
    by_category = _group(records, "label")
    by_day = _group(records, "date")
    by_day_category = _group_by_day_and_label(records)
    total_seconds = sum(int(row["total_seconds"] or 0) for row in records)
    productive_seconds = sum(
        int(row["total_seconds"] or 0)
        for row in records
        if row["label"] in {"Projeto", "Produtivo", "Estudo"}
    )
    risk_seconds = sum(
        int(row["total_seconds"] or 0)
        for row in records
        if row["label"] in {"Risco", "Distracao"}
    )
    score_seconds = sum(
        int(row["total_seconds"] or 0) * score_for_label(row["label"])
        for row in records
    )
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_seconds": total_seconds,
        "total_minutes": round(total_seconds / 60, 1),
        "productive_seconds": productive_seconds,
        "productive_minutes": round(productive_seconds / 60, 1),
        "neutral_seconds": sum(item["seconds"] for item in by_category if item["label"] in {"Neutro", "Comunicacao"}),
        "neutral_minutes": round(sum(item["seconds"] for item in by_category if item["label"] in {"Neutro", "Comunicacao"}) / 60, 1),
        "risk_seconds": risk_seconds,
        "risk_minutes": round(risk_seconds / 60, 1),
        "distraction_seconds": risk_seconds,
        "distraction_minutes": round(risk_seconds / 60, 1),
        "score": round(score_seconds / 60, 1),
        "result": _result_text(score_seconds, productive_seconds, risk_seconds),
        "by_app": by_app,
        "by_category": by_category,
        "by_day": by_day,
        "by_day_category": by_day_category,
        "top_app": by_app[0] if by_app else None,
        "top_category": by_category[0] if by_category else None,
        "apps_count": len(by_app),
    }


def delete_usage_data(scope: str = "today") -> dict:
    from backend.database import get_connection

    today = date.today()
    params: tuple = ()
    if scope == "all":
        where = "1 = 1"
    elif scope == "last7":
        where = "date >= ?"
        params = ((today - timedelta(days=6)).isoformat(),)
    else:
        where = "date = ?"
        params = (today.isoformat(),)
    with get_connection() as conn:
        cursor = conn.execute(f"DELETE FROM {TABLE_NAME} WHERE {where}", params)
    return {"deleted": cursor.rowcount if cursor.rowcount is not None else 0, "scope": scope}


def _group(records: list[dict], key: str) -> list[dict]:
    totals: dict[str, int] = {}
    for row in records:
        label = str(row.get(key) or "Neutro")
        totals[label] = totals.get(label, 0) + int(row.get("total_seconds") or 0)
    return [
        {"label": label, "seconds": seconds, "minutes": round(seconds / 60, 1)}
        for label, seconds in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def _group_apps(records: list[dict]) -> list[tuple[str, dict]]:
    totals: dict[str, dict] = {}
    for row in records:
        app_name = str(row.get("app_name") or "Desconhecido")
        item = totals.setdefault(app_name, {"seconds": 0, "labels": {}})
        seconds = int(row.get("total_seconds") or 0)
        label = str(row.get("label") or "Neutro")
        item["seconds"] += seconds
        item["labels"][label] = item["labels"].get(label, 0) + seconds
    grouped: list[tuple[str, dict]] = []
    for app_name, item in totals.items():
        dominant_label = max(item["labels"].items(), key=lambda value: value[1])[0]
        grouped.append((app_name, {"seconds": item["seconds"], "label": dominant_label}))
    return sorted(grouped, key=lambda value: (-value[1]["seconds"], value[0].lower()))


def _group_by_day_and_label(records: list[dict]) -> list[dict]:
    totals: dict[tuple[str, str], int] = {}
    for row in records:
        day = str(row.get("date") or "")
        label = str(row.get("label") or "Neutro")
        if not day:
            continue
        key = (day, label)
        totals[key] = totals.get(key, 0) + int(row.get("total_seconds") or 0)
    return [
        {"date": day, "label": label, "seconds": seconds, "minutes": round(seconds / 60, 1)}
        for (day, label), seconds in sorted(totals.items(), key=lambda item: (item[0][0], item[0][1]))
    ]


def _result_text(score_seconds: float, productive_seconds: int, risk_seconds: int) -> str:
    if not productive_seconds and not risk_seconds:
        return "Sem dados suficientes ainda."
    if score_seconds > 0:
        return "Dia mais produtivo do que disperso."
    if score_seconds < 0:
        return "Dia com mais dispersao do que producao."
    return "Dia equilibrado entre foco e dispersao."
