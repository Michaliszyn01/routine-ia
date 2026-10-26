from __future__ import annotations

from datetime import date

from .database import get_connection
from .validators import sanitize_text, validate_date


TASK_AREAS = {"rotina", "estudos", "saude", "projetos", "pessoal"}
TASK_STATUSES = {"pending", "in_progress", "completed", "archived"}


def list_tasks(
    *,
    status: str | None = None,
    area: str | None = None,
    reference_date: str | None = None,
    include_archived: bool = False,
) -> list[dict]:
    clauses: list[str] = []
    params: list[object] = []
    if status:
        if status not in TASK_STATUSES:
            raise ValueError("Status de tarefa invalido.")
        clauses.append("t.status = ?")
        params.append(status)
    elif not include_archived:
        clauses.append("t.status != 'archived'")
    if area:
        normalized_area = _area(area)
        clauses.append("t.area = ?")
        params.append(normalized_area)
    if reference_date:
        day = validate_date(reference_date)
        clauses.append("(t.scheduled_for = ? OR t.due_date = ?)")
        params.extend([day, day])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT t.*, p.name AS project_name
            FROM tasks t
            LEFT JOIN projects p ON p.id = t.project_id
            {where}
            ORDER BY
                CASE t.status WHEN 'in_progress' THEN 0 WHEN 'pending' THEN 1 WHEN 'completed' THEN 2 ELSE 3 END,
                CASE WHEN t.due_date IS NOT NULL AND t.due_date < date('now', 'localtime') THEN 0 ELSE 1 END,
                t.priority DESC,
                COALESCE(t.scheduled_for, t.due_date, '9999-12-31'),
                t.sort_order,
                t.id DESC
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_task(task_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT t.*, p.name AS project_name
            FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
            WHERE t.id = ?
            """,
            (task_id,),
        ).fetchone()
    return dict(row) if row else None


def create_task(payload: dict) -> dict:
    data = _payload(payload)
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (
                title, notes, area, status, priority, due_date, scheduled_for,
                estimated_minutes, subject, source, project_id, parent_task_id, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["title"], data["notes"], data["area"], data["status"], data["priority"],
                data["due_date"], data["scheduled_for"], data["estimated_minutes"],
                data["subject"], data["source"], data["project_id"], data["parent_task_id"],
                data["sort_order"],
            ),
        )
        task_id = int(cursor.lastrowid)
    return get_task(task_id) or {}


def update_task(task_id: int, payload: dict) -> dict:
    existing = get_task(task_id)
    if not existing:
        raise LookupError("Tarefa nao encontrada.")
    merged = {**existing, **payload}
    data = _payload(merged)
    completed_at = "CURRENT_TIMESTAMP" if data["status"] == "completed" else "NULL"
    with get_connection() as connection:
        connection.execute(
            f"""
            UPDATE tasks SET
                title = ?, notes = ?, area = ?, status = ?, priority = ?, due_date = ?,
                scheduled_for = ?, estimated_minutes = ?, subject = ?, source = ?,
                project_id = ?, parent_task_id = ?, sort_order = ?,
                completed_at = {completed_at}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                data["title"], data["notes"], data["area"], data["status"], data["priority"],
                data["due_date"], data["scheduled_for"], data["estimated_minutes"],
                data["subject"], data["source"], data["project_id"], data["parent_task_id"],
                data["sort_order"], task_id,
            ),
        )
    return get_task(task_id) or {}


def complete_task(task_id: int, completed: bool = True) -> dict:
    return update_task(task_id, {"status": "completed" if completed else "pending"})


def archive_task(task_id: int) -> dict:
    return update_task(task_id, {"status": "archived"})


def task_overview(reference_date: str | None = None) -> dict:
    day = validate_date(reference_date or date.today().isoformat())
    active = [item for item in list_tasks() if item["status"] in {"pending", "in_progress"}]
    today_items = [
        item for item in active if item.get("scheduled_for") == day or item.get("due_date") == day
    ]
    overdue = [item for item in active if item.get("due_date") and item["due_date"] < day]
    completed_today = []
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT t.*, p.name AS project_name
            FROM tasks t LEFT JOIN projects p ON p.id = t.project_id
            WHERE t.status = 'completed' AND date(t.completed_at, 'localtime') = ?
            ORDER BY t.completed_at DESC
            """,
            (day,),
        ).fetchall()
        completed_today = [dict(row) for row in rows]
    return {
        "date": day,
        "today": today_items,
        "overdue": overdue,
        "backlog": [item for item in active if item not in today_items and item not in overdue][:8],
        "completed_today": completed_today,
        "counts": {
            "today": len(today_items),
            "overdue": len(overdue),
            "backlog": max(0, len(active) - len(today_items) - len(overdue)),
            "completed_today": len(completed_today),
        },
    }


def _payload(payload: dict) -> dict:
    title = sanitize_text(payload.get("title"), 180)
    if not title:
        raise ValueError("Informe o titulo da tarefa.")
    status = str(payload.get("status") or "pending").strip().lower()
    if status not in TASK_STATUSES:
        raise ValueError("Status de tarefa invalido.")
    priority = _int(payload.get("priority"), 2)
    if priority not in {1, 2, 3, 4}:
        raise ValueError("Prioridade precisa estar entre 1 e 4.")
    estimated_minutes = _int(payload.get("estimated_minutes"), 25)
    if not 1 <= estimated_minutes <= 1440:
        raise ValueError("Duracao estimada precisa estar entre 1 e 1440 minutos.")
    return {
        "title": title,
        "notes": sanitize_text(payload.get("notes"), 2000),
        "area": _area(payload.get("area")),
        "status": status,
        "priority": priority,
        "due_date": _optional_date(payload.get("due_date")),
        "scheduled_for": _optional_date(payload.get("scheduled_for")),
        "estimated_minutes": estimated_minutes,
        "subject": sanitize_text(payload.get("subject"), 100),
        "source": sanitize_text(payload.get("source") or "manual", 40),
        "project_id": _optional_int(payload.get("project_id")),
        "parent_task_id": _optional_int(payload.get("parent_task_id")),
        "sort_order": _int(payload.get("sort_order"), 0),
    }


def _area(value: object) -> str:
    area = str(value or "rotina").strip().lower()
    aliases = {"estudo": "estudos", "projeto": "projetos", "saude": "saude"}
    area = aliases.get(area, area)
    if area not in TASK_AREAS:
        raise ValueError("Area de tarefa invalida.")
    return area


def _optional_date(value: object) -> str | None:
    return validate_date(str(value)) if value not in {None, ""} else None


def _optional_int(value: object) -> int | None:
    return _int(value, 0) or None


def _int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
