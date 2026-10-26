from __future__ import annotations

import json
from datetime import date, datetime

from .database import get_connection
from .validators import bounded_int, sanitize_text, validate_date


def list_checklists(date_value: str | None = None, context: str | None = None) -> dict:
    date_value = validate_date(date_value or date.today().isoformat())
    templates = _templates()
    suggested = _suggest_template(templates, context)
    return {
        "date": date_value,
        "suggested": suggested,
        "templates": templates,
    }


def log_checklist(payload: dict) -> dict:
    template_id = bounded_int(payload.get("template_id"), "template_id", "Checklist", minimum=1)
    date_value = validate_date(payload.get("date") or date.today().isoformat())
    completed_items = payload.get("completed_items") or payload.get("completed_items_json") or []
    if not isinstance(completed_items, list):
        completed_items = []
    completed_items = [bounded_int(item, "item", "Item", minimum=1) for item in completed_items if str(item).strip()]
    note = sanitize_text(payload.get("note"), 1000)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO checklist_logs (template_id, date, completed_items_json, note, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (template_id, date_value, json.dumps(completed_items), note),
        )
        row = conn.execute("SELECT * FROM checklist_logs WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return {"log": dict(row), "feedback": "Checklist salvo. Voce reduziu a friccao do proximo passo."}


def checklist_summary(start: str, end: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM checklist_logs WHERE date >= ? AND date <= ?",
            (start, end),
        ).fetchall()
    return {"count": len(rows), "logs": [dict(row) for row in rows]}


def _templates() -> list[dict]:
    with get_connection() as conn:
        template_rows = conn.execute(
            "SELECT * FROM checklist_templates WHERE active = 1 ORDER BY id ASC"
        ).fetchall()
        item_rows = conn.execute(
            "SELECT * FROM checklist_items ORDER BY template_id ASC, order_index ASC, id ASC"
        ).fetchall()
    items_by_template: dict[int, list[dict]] = {}
    for row in item_rows:
        item = dict(row)
        items_by_template.setdefault(int(item["template_id"]), []).append(item)
    templates = []
    for row in template_rows:
        template = dict(row)
        template["items"] = items_by_template.get(int(template["id"]), [])
        templates.append(template)
    return templates


def _suggest_template(templates: list[dict], context: str | None) -> dict | None:
    context_value = (context or "").lower()
    if not context_value:
        hour = datetime.now().hour
        context_value = "sono" if hour >= 21 else "estudo"
    if "program" in context_value or "codigo" in context_value:
        wanted = "programacao"
    elif "sono" in context_value or "dorm" in context_value or "noite" in context_value:
        wanted = "sono"
    elif "ruim" in context_value or "trav" in context_value:
        wanted = "bad_day"
    elif "sair" in context_value or "casa" in context_value:
        wanted = "saida"
    else:
        wanted = "estudo"
    return next((template for template in templates if template.get("category") == wanted), templates[0] if templates else None)
