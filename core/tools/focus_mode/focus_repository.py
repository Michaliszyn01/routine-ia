from __future__ import annotations

import json
from datetime import date

from backend.database import get_connection


ACTIVE_STATUSES = {"active", "paused"}


def ensure_focus_schema() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS focus_session_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES focus_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS focus_app_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                app_name TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT 'Neutro',
                seconds INTEGER NOT NULL DEFAULT 0,
                match_status TEXT NOT NULL DEFAULT 'match',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES focus_sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_focus_events_session ON focus_session_events(session_id);
            CREATE INDEX IF NOT EXISTS idx_focus_app_usage_session ON focus_app_usage(session_id);
            """
        )
        for column, definition in {
            "plan_block_id": "INTEGER",
            "title": "TEXT NOT NULL DEFAULT ''",
            "focus_type": "TEXT NOT NULL DEFAULT 'generic'",
            "planned_minutes": "INTEGER NOT NULL DEFAULT 25",
            "actual_seconds": "INTEGER NOT NULL DEFAULT 0",
            "focused_seconds": "INTEGER NOT NULL DEFAULT 0",
            "distracted_seconds": "INTEGER NOT NULL DEFAULT 0",
            "status": "TEXT NOT NULL DEFAULT 'pending'",
            "completion_note": "TEXT NOT NULL DEFAULT ''",
            "updated_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        }.items():
            _ensure_column(conn, "focus_sessions", column, definition)
        conn.execute(
            """
            UPDATE focus_sessions
            SET title = CASE WHEN title = '' THEN COALESCE(note, '') ELSE title END,
                focus_type = CASE
                    WHEN focus_type = 'generic' AND category = 'estudo' THEN 'study'
                    WHEN focus_type = 'generic' AND category = 'programacao' THEN 'project'
                    WHEN focus_type = 'generic' AND category = 'leitura' THEN 'reading'
                    ELSE focus_type
                END,
                planned_minutes = CASE WHEN planned_minutes = 25 THEN duration_minutes ELSE planned_minutes END,
                status = CASE
                    WHEN status = 'pending' AND completed = 1 THEN 'completed'
                    WHEN status = 'pending' AND completed = 0 AND ended_at IS NOT NULL THEN 'abandoned'
                    ELSE status
                END
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_focus_sessions_status ON focus_sessions(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_focus_sessions_plan_block ON focus_sessions(plan_block_id)")


def get_plan_block(block_id: int) -> dict | None:
    ensure_focus_schema()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT b.*, p.date
            FROM daily_plan_blocks b
            JOIN daily_plans p ON p.id = b.plan_id
            WHERE b.id = ?
            """,
            (block_id,),
        ).fetchone()
    return dict(row) if row else None


def active_session() -> dict | None:
    ensure_focus_schema()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM focus_sessions
            WHERE status IN ('active', 'paused')
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
    return dict(row) if row else None


def create_session(data: dict) -> dict:
    ensure_focus_schema()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM focus_sessions WHERE status IN ('active', 'paused') ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if existing:
            raise ValueError("Ja existe uma sessao de foco ativa.")
        cursor = conn.execute(
            """
            INSERT INTO focus_sessions (
                date, plan_block_id, title, focus_type, planned_minutes,
                project_id, category, duration_minutes, break_minutes,
                completed, started_at, note, status, completion_note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, ?, 'active', '')
            """,
            (
                data["date"],
                data.get("plan_block_id"),
                data["title"],
                data["focus_type"],
                data["planned_minutes"],
                data.get("project_id"),
                data.get("category"),
                data["planned_minutes"],
                data.get("break_minutes", 0),
                data.get("next_step", ""),
            ),
        )
        session_id = int(cursor.lastrowid)
        log_event(conn, session_id, "started", {"source": data.get("source", "focus_mode")})
        row = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
    return session_payload(dict(row))


def update_status(session_id: int, status: str, event_type: str, metadata: dict | None = None) -> dict:
    ensure_focus_schema()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise ValueError("Sessao de foco nao encontrada.")
        conn.execute(
            "UPDATE focus_sessions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, session_id),
        )
        log_event(conn, session_id, event_type, metadata or {})
        updated = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
    return session_payload(dict(updated))


def finish_session(session_id: int, status: str, note: str = "", actual_seconds: int | None = None) -> dict:
    ensure_focus_schema()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise ValueError("Sessao de foco nao encontrada.")
        totals = app_usage_totals(conn, session_id)
        actual = max(int(actual_seconds or 0), totals["focused_seconds"] + totals["distracted_seconds"])
        if not actual:
            actual = _wall_seconds(dict(row))
        conn.execute(
            """
            UPDATE focus_sessions
            SET status = ?, completed = ?, ended_at = CURRENT_TIMESTAMP,
                actual_seconds = ?, focused_seconds = ?, distracted_seconds = ?,
                completion_note = ?, note = CASE WHEN ? != '' THEN ? ELSE note END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                status,
                1 if status == "completed" else 0,
                actual,
                totals["focused_seconds"],
                totals["distracted_seconds"],
                note,
                note,
                note,
                session_id,
            ),
        )
        log_event(conn, session_id, status, {"note": note})
        updated = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
    return session_payload(dict(updated))


def add_app_usage(session_id: int, app_name: str, label: str, seconds: int, match_status: str) -> dict:
    ensure_focus_schema()
    amount = max(0, int(seconds or 0))
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise ValueError("Sessao de foco nao encontrada.")
        if amount:
            conn.execute(
                """
                INSERT INTO focus_app_usage (session_id, app_name, label, seconds, match_status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, app_name or "Desconhecido", label or "Neutro", amount, match_status),
            )
            totals = app_usage_totals(conn, session_id)
            conn.execute(
                """
                UPDATE focus_sessions
                SET focused_seconds = ?, distracted_seconds = ?, actual_seconds = MAX(actual_seconds, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    totals["focused_seconds"],
                    totals["distracted_seconds"],
                    totals["focused_seconds"] + totals["distracted_seconds"],
                    session_id,
                ),
            )
        event = "app_match" if match_status == "match" else "app_mismatch"
        log_event(conn, session_id, event, {"app_name": app_name, "label": label, "seconds": amount, "match_status": match_status})
        updated = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
    return session_payload(dict(updated))


def get_session(session_id: int) -> dict | None:
    ensure_focus_schema()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM focus_sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return None
        payload = session_payload(dict(row))
        payload["app_usage"] = list_app_usage(conn, session_id)
        payload["events"] = [dict(item) for item in conn.execute("SELECT * FROM focus_session_events WHERE session_id = ? ORDER BY id ASC", (session_id,)).fetchall()]
    return payload


def list_sessions(start: str, end: str, limit: int = 80) -> list[dict]:
    ensure_focus_schema()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM focus_sessions
            WHERE date >= ? AND date <= ?
            ORDER BY started_at DESC, id DESC
            LIMIT ?
            """,
            (start, end, limit),
        ).fetchall()
    return [session_payload(dict(row)) for row in rows]


def summary(start: str, end: str) -> dict:
    ensure_focus_schema()
    sessions = list_sessions(start, end, limit=1000)
    completed = [item for item in sessions if item["status"] == "completed"]
    abandoned = [item for item in sessions if item["status"] == "abandoned"]
    focused = sum(int(item.get("focused_seconds") or 0) for item in sessions)
    distracted = sum(int(item.get("distracted_seconds") or 0) for item in sessions)
    best = max(sessions, key=lambda item: int(item.get("focused_seconds") or 0), default=None)
    types: dict[str, int] = {}
    for item in sessions:
        types[item["focus_type"]] = types.get(item["focus_type"], 0) + 1
    return {
        "sessions": len(sessions),
        "completed": len(completed),
        "abandoned": len(abandoned),
        "focused_seconds": focused,
        "focused_minutes": round(focused / 60, 1),
        "focused_hours": round(focused / 3600, 2),
        "distracted_seconds": distracted,
        "distracted_minutes": round(distracted / 60, 1),
        "best_session": best,
        "top_focus_type": max(types.items(), key=lambda item: item[1])[0] if types else "",
        "sessions_list": sessions,
    }


def top_breakers(start: str, end: str, limit: int = 6) -> list[dict]:
    ensure_focus_schema()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.app_name, u.label, SUM(u.seconds) AS seconds
            FROM focus_app_usage u
            JOIN focus_sessions s ON s.id = u.session_id
            WHERE s.date >= ? AND s.date <= ? AND u.match_status IN ('warning', 'mismatch')
            GROUP BY u.app_name, u.label
            ORDER BY seconds DESC, u.app_name ASC
            LIMIT ?
            """,
            (start, end, limit),
        ).fetchall()
    return [
        {"app_name": row["app_name"], "label": row["label"], "seconds": int(row["seconds"] or 0), "minutes": round(int(row["seconds"] or 0) / 60, 1)}
        for row in rows
    ]


def log_event(conn, session_id: int, event_type: str, metadata: dict | None = None) -> None:
    conn.execute(
        """
        INSERT INTO focus_session_events (session_id, event_type, metadata)
        VALUES (?, ?, ?)
        """,
        (session_id, event_type, json.dumps(metadata or {}, ensure_ascii=True)),
    )


def list_app_usage(conn, session_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT app_name, label, match_status, SUM(seconds) AS seconds
        FROM focus_app_usage
        WHERE session_id = ?
        GROUP BY app_name, label, match_status
        ORDER BY seconds DESC, app_name ASC
        """,
        (session_id,),
    ).fetchall()
    return [
        {"app_name": row["app_name"], "label": row["label"], "match_status": row["match_status"], "seconds": int(row["seconds"] or 0), "minutes": round(int(row["seconds"] or 0) / 60, 1)}
        for row in rows
    ]


def app_usage_totals(conn, session_id: int) -> dict:
    rows = conn.execute(
        "SELECT match_status, SUM(seconds) AS seconds FROM focus_app_usage WHERE session_id = ? GROUP BY match_status",
        (session_id,),
    ).fetchall()
    focused = sum(int(row["seconds"] or 0) for row in rows if row["match_status"] == "match")
    distracted = sum(int(row["seconds"] or 0) for row in rows if row["match_status"] != "match")
    return {"focused_seconds": focused, "distracted_seconds": distracted}


def session_payload(row: dict) -> dict:
    planned = int(row.get("planned_minutes") or row.get("duration_minutes") or 25)
    focus_type = row.get("focus_type") or "generic"
    title = row.get("title") or row.get("note") or _title_for_type(focus_type)
    status = row.get("status") or ("completed" if int(row.get("completed") or 0) else "pending")
    return {
        **row,
        "title": title,
        "focus_type": focus_type,
        "planned_minutes": planned,
        "duration_minutes": int(row.get("duration_minutes") or planned),
        "actual_seconds": int(row.get("actual_seconds") or 0),
        "focused_seconds": int(row.get("focused_seconds") or 0),
        "distracted_seconds": int(row.get("distracted_seconds") or 0),
        "status": status,
    }


def _ensure_column(conn, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _wall_seconds(row: dict) -> int:
    started = str(row.get("started_at") or "")
    ended = str(row.get("ended_at") or "")
    try:
        from datetime import datetime

        start_dt = datetime.fromisoformat(started.replace(" ", "T"))
        end_dt = datetime.fromisoformat(ended.replace(" ", "T")) if ended else datetime.now()
        return max(0, int((end_dt - start_dt).total_seconds()))
    except ValueError:
        return int(row.get("planned_minutes") or row.get("duration_minutes") or 0) * 60


def _title_for_type(focus_type: str) -> str:
    return {
        "study": "Bloco de estudo",
        "project": "Bloco de projeto",
        "workout": "Treino",
        "organization": "Organizacao",
        "reading": "Leitura",
        "rest": "Descanso",
    }.get(focus_type, "Foco rapido")
