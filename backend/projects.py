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


PROJECT_CATEGORIES = {"Estudos", "Programacao", "Trabalho", "Saude", "Pessoal", "Outro"}
PROJECT_STATUSES = {"ativo", "pausado", "concluido", "arquivado"}
TIME_SOURCES = {"manual", "focus_timer"}


def list_projects(include_archived: bool = False) -> list[dict]:
    query = """
        SELECT p.*,
               COALESCE(SUM(CASE WHEN e.date >= ? AND e.date <= ? THEN e.minutes ELSE 0 END), 0) AS week_minutes
        FROM projects p
        LEFT JOIN project_time_entries e ON e.project_id = p.id
    """
    start, end = week_range()
    params: list = [start, end]
    if not include_archived:
        query += " WHERE p.status != 'arquivado' AND p.active = 1"
    query += " GROUP BY p.id ORDER BY p.active DESC, p.status ASC, p.updated_at DESC, p.name ASC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_project_dict(row) for row in rows]


def get_project(project_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project_dict(row) if row else None


def save_project(payload: dict, project_id: int | None = None) -> dict:
    data = validate_project_payload(payload)
    with get_connection() as conn:
        if project_id:
            conn.execute(
                """
                UPDATE projects
                SET name = ?,
                    description = ?,
                    category = ?,
                    status = ?,
                    color = ?,
                    weekly_hours_goal = ?,
                    active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    data["name"],
                    data["description"],
                    data["category"],
                    data["status"],
                    data["color"],
                    data["weekly_hours_goal"],
                    data["active"],
                    project_id,
                ),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    name, description, category, status, color, weekly_hours_goal, active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"],
                    data["description"],
                    data["category"],
                    data["status"],
                    data["color"],
                    data["weekly_hours_goal"],
                    data["active"],
                ),
            )
            project_id = int(cursor.lastrowid)
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project_dict(row)


def archive_project(project_id: int) -> dict:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE projects
            SET status = 'arquivado', active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (project_id,),
        )
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project_dict(row)


def list_project_time(project_id: int, start: str | None = None, end: str | None = None) -> list[dict]:
    query = """
        SELECT e.*, p.name AS project_name, p.color AS project_color
        FROM project_time_entries e
        JOIN projects p ON p.id = e.project_id
        WHERE e.project_id = ?
    """
    params: list = [project_id]
    if start:
        query += " AND e.date >= ?"
        params.append(start)
    if end:
        query += " AND e.date <= ?"
        params.append(end)
    query += " ORDER BY e.date DESC, e.id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def add_project_time(project_id: int, payload: dict) -> dict:
    data = validate_time_payload(payload)
    with get_connection() as conn:
        conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
        cursor = conn.execute(
            """
            INSERT INTO project_time_entries (project_id, date, minutes, source, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, data["date"], data["minutes"], data["source"], data["note"]),
        )
        row = conn.execute(
            """
            SELECT e.*, p.name AS project_name, p.color AS project_color
            FROM project_time_entries e
            JOIN projects p ON p.id = e.project_id
            WHERE e.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return _row_to_dict(row)


def project_summary(reference_date: str | None = None) -> dict:
    start, end = week_range(reference_date)
    with get_connection() as conn:
        project_rows = conn.execute(
            """
            SELECT p.id, p.name, p.color, p.weekly_hours_goal,
                   COALESCE(SUM(e.minutes), 0) AS minutes
            FROM projects p
            LEFT JOIN project_time_entries e
              ON e.project_id = p.id AND e.date >= ? AND e.date <= ?
            WHERE p.active = 1 AND p.status != 'arquivado'
            GROUP BY p.id
            ORDER BY minutes DESC, p.name ASC
            """,
            (start, end),
        ).fetchall()
        day_rows = conn.execute(
            """
            SELECT date, COALESCE(SUM(minutes), 0) AS minutes
            FROM project_time_entries
            WHERE date >= ? AND date <= ?
            GROUP BY date
            """,
            (start, end),
        ).fetchall()

    projects = [_project_hours_dict(row) for row in project_rows]
    top_project = projects[0] if projects and projects[0]["minutes"] > 0 else None
    below_goal = [
        item for item in projects
        if item["weekly_hours_goal"] > 0 and item["hours"] < item["weekly_hours_goal"]
    ]
    by_date = {row["date"]: int(row["minutes"] or 0) for row in day_rows}
    labels = []
    minutes_by_day = []
    start_date = _parse_date(start)
    for index in range(7):
        current = start_date + timedelta(days=index)
        labels.append(["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"][index])
        minutes_by_day.append(round(by_date.get(current.isoformat(), 0) / 60, 2))

    return {
        "week_start": start,
        "week_end": end,
        "active_projects": len(projects),
        "total_minutes": sum(item["minutes"] for item in projects),
        "total_hours": round(sum(item["minutes"] for item in projects) / 60, 2),
        "top_project": top_project,
        "below_goal": below_goal,
        "projects": projects,
        "labels": labels,
        "hours_by_day": minutes_by_day,
        "hours_by_project": {item["name"]: item["hours"] for item in projects},
    }


def hours_by_project(start: str, end: str) -> dict[str, float]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.name, COALESCE(SUM(e.minutes), 0) AS minutes
            FROM project_time_entries e
            JOIN projects p ON p.id = e.project_id
            WHERE e.date >= ? AND e.date <= ?
            GROUP BY p.id, p.name
            ORDER BY minutes DESC
            """,
            (start, end),
        ).fetchall()
    return {row["name"]: round(float(row["minutes"] or 0) / 60, 2) for row in rows}


def week_range(reference_date: str | None = None) -> tuple[str, str]:
    current = _parse_date(reference_date or date.today().isoformat())
    start = current - timedelta(days=current.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def validate_project_payload(payload: dict) -> dict:
    name = sanitize_text(payload.get("name"), 120)
    if not name:
        raise ValueError("Nome do projeto obrigatorio.")
    category = sanitize_text(payload.get("category") or "Outro", 40)
    if category not in PROJECT_CATEGORIES:
        category = "Outro"
    status = sanitize_text(payload.get("status") or "ativo", 40)
    if status not in PROJECT_STATUSES:
        status = "ativo"
    color = sanitize_text(payload.get("color") or "#22d3ee", 20)
    if not color.startswith("#") or len(color) not in {4, 7}:
        color = "#22d3ee"
    return {
        "name": name,
        "description": sanitize_text(payload.get("description"), 2000),
        "category": category,
        "status": status,
        "color": color,
        "weekly_hours_goal": bounded_float(
            payload.get("weekly_hours_goal"),
            "weekly_hours_goal",
            "Meta semanal",
            maximum=168,
        ),
        "active": bool_to_int(payload.get("active", True)),
    }


def validate_time_payload(payload: dict) -> dict:
    source = sanitize_text(payload.get("source") or "manual", 40)
    if source not in TIME_SOURCES:
        source = "manual"
    return {
        "date": validate_date(payload.get("date") or date.today().isoformat()),
        "minutes": bounded_int(payload.get("minutes"), "minutes", "Minutos", minimum=1, maximum=1440),
        "source": source,
        "note": sanitize_text(payload.get("note"), 1000),
    }


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _row_to_dict(row) -> dict:
    return dict(row)


def _project_dict(row) -> dict:
    data = dict(row)
    data["weekly_hours_goal"] = float(data.get("weekly_hours_goal") or 0)
    data["active"] = int(data.get("active") or 0)
    if "week_minutes" in data:
        data["week_minutes"] = int(data.get("week_minutes") or 0)
        data["week_hours"] = round(data["week_minutes"] / 60, 2)
    return data


def _project_hours_dict(row) -> dict:
    minutes = int(row["minutes"] or 0)
    goal = float(row["weekly_hours_goal"] or 0)
    return {
        "id": row["id"],
        "name": row["name"],
        "color": row["color"],
        "weekly_hours_goal": goal,
        "minutes": minutes,
        "hours": round(minutes / 60, 2),
        "goal_percent": round((minutes / 60) / goal * 100, 1) if goal else 0,
    }
