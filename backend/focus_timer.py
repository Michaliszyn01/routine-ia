from __future__ import annotations

from datetime import date, datetime

from .database import get_connection
from .projects import add_project_time
from .validators import bounded_int, sanitize_text, validate_date


FOCUS_CATEGORIES = {"estudo", "programacao", "leitura", "trabalho", "outro"}
DAILY_CATEGORY_MAP = {
    "estudo": ("study_done", "study_hours"),
    "programacao": ("programming_done", "programming_hours"),
    "leitura": ("reading_done", "reading_hours"),
}


def start_focus_session(payload: dict) -> dict:
    data = validate_focus_payload(payload, completed=False)
    started_at = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO focus_sessions (
                date, project_id, category, duration_minutes, break_minutes,
                completed, started_at, note
            )
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                data["date"],
                data["project_id"],
                data["category"],
                data["duration_minutes"],
                data["break_minutes"],
                started_at,
                data["note"],
            ),
        )
        row = _fetch_session(conn, int(cursor.lastrowid))
    return _row_to_dict(row)


def complete_focus_session(session_id: int, payload: dict | None = None) -> dict:
    payload = payload or {}
    ended_at = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        existing = _fetch_session(conn, session_id)
        if not existing:
            raise ValueError("Sessao de foco nao encontrada.")
        was_completed = int(existing["completed"] or 0)
        note = sanitize_text(payload.get("note") or existing["note"], 1000)
        conn.execute(
            """
            UPDATE focus_sessions
            SET completed = 1, ended_at = ?, note = ?
            WHERE id = ?
            """,
            (ended_at, note, session_id),
        )
        row = _fetch_session(conn, session_id)

    session = _row_to_dict(row)
    if not was_completed:
        _mirror_completed_focus(session, payload)
    return session


def save_focus_session(payload: dict) -> dict:
    data = validate_focus_payload(payload, completed=True)
    started_at = payload.get("started_at") or datetime.now().isoformat(timespec="seconds")
    ended_at = payload.get("ended_at") or datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO focus_sessions (
                date, project_id, category, duration_minutes, break_minutes,
                completed, started_at, ended_at, note
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                data["date"],
                data["project_id"],
                data["category"],
                data["duration_minutes"],
                data["break_minutes"],
                started_at,
                ended_at,
                data["note"],
            ),
        )
        row = _fetch_session(conn, int(cursor.lastrowid))
    session = _row_to_dict(row)
    _mirror_completed_focus(session, payload)
    return session


def list_focus_sessions(start: str | None = None, end: str | None = None, limit: int = 80) -> list[dict]:
    query = """
        SELECT f.*, p.name AS project_name, p.color AS project_color
        FROM focus_sessions f
        LEFT JOIN projects p ON p.id = f.project_id
    """
    params: list = []
    clauses = []
    if start:
        clauses.append("f.date >= ?")
        params.append(start)
    if end:
        clauses.append("f.date <= ?")
        params.append(end)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY f.date DESC, f.started_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]


def focus_summary(start: str, end: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT date,
                   COUNT(*) AS sessions,
                   COALESCE(SUM(duration_minutes), 0) AS minutes
            FROM focus_sessions
            WHERE completed = 1 AND date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
            """,
            (start, end),
        ).fetchall()
    return {
        "sessions": sum(int(row["sessions"] or 0) for row in rows),
        "minutes": sum(int(row["minutes"] or 0) for row in rows),
        "hours": round(sum(int(row["minutes"] or 0) for row in rows) / 60, 2),
        "by_date": {row["date"]: int(row["minutes"] or 0) for row in rows},
    }


def validate_focus_payload(payload: dict, completed: bool) -> dict:
    category = sanitize_text(payload.get("category") or "outro", 40)
    if category not in FOCUS_CATEGORIES:
        category = "outro"
    project_id = payload.get("project_id")
    try:
        project_id = int(project_id) if project_id not in (None, "", "null") else None
    except (TypeError, ValueError):
        project_id = None
    return {
        "date": validate_date(payload.get("date") or date.today().isoformat()),
        "project_id": project_id,
        "category": category,
        "duration_minutes": bounded_int(
            payload.get("duration_minutes"),
            "duration_minutes",
            "Duracao",
            minimum=1,
            maximum=720,
            default=25,
        ),
        "break_minutes": bounded_int(
            payload.get("break_minutes"),
            "break_minutes",
            "Pausa",
            minimum=0,
            maximum=120,
            default=5,
        ),
        "completed": int(completed),
        "note": sanitize_text(payload.get("note"), 1000),
    }


def _mirror_completed_focus(session: dict, payload: dict) -> None:
    project_id = session.get("project_id")
    if project_id:
        add_project_time(
            int(project_id),
            {
                "date": session["date"],
                "minutes": session["duration_minutes"],
                "source": "focus_timer",
                "note": session.get("note") or "Sessao de foco",
            },
        )

    if payload.get("apply_to_daily"):
        apply_focus_to_daily_record(session)


def apply_focus_to_daily_record(session: dict) -> None:
    mapping = DAILY_CATEGORY_MAP.get(session.get("category"))
    if not mapping:
        return
    done_field, hours_field = mapping
    from . import models

    record = models.get_daily_record(session["date"]) or {
        "date": session["date"],
        "workout_done": 0,
        "workout_hours": 0,
        "study_done": 0,
        "study_hours": 0,
        "programming_done": 0,
        "programming_hours": 0,
        "game_hours": 0,
        "reading_done": 0,
        "reading_hours": 0,
        "sleep_hours": 0,
        "steps": 0,
        "energy": 3,
        "mood": 3,
        "observation": "",
    }
    record[done_field] = 1
    record[hours_field] = round(float(record.get(hours_field) or 0) + int(session["duration_minutes"]) / 60, 2)
    models.upsert_daily_record(record)


def _fetch_session(conn, session_id: int):
    return conn.execute(
        """
        SELECT f.*, p.name AS project_name, p.color AS project_color
        FROM focus_sessions f
        LEFT JOIN projects p ON p.id = f.project_id
        WHERE f.id = ?
        """,
        (session_id,),
    ).fetchone()


def _row_to_dict(row) -> dict:
    return dict(row)
