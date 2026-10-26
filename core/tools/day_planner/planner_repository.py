from __future__ import annotations

from datetime import date

from backend.database import get_connection


def ensure_day_planner_schema() -> None:
    with get_connection() as conn:
        conn.executescript(DAY_PLANNER_SCHEMA)


def get_latest_checkin(date_value: str) -> dict | None:
    ensure_day_planner_schema()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM daily_energy_checkins
            WHERE date = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (date_value,),
        ).fetchone()
    return dict(row) if row else None


def save_checkin(payload: dict) -> dict:
    ensure_day_planner_schema()
    date_value = _date(payload.get("date"))
    energy = _clean_choice(payload.get("energy_level"), {"baixa", "media", "alta"}, "media")
    focus = _clean_choice(payload.get("focus_level"), {"baixo", "medio", "alto", ""}, "")
    mood = _clean_choice(payload.get("mood_level"), {"ruim", "ok", "bom", ""}, "")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO daily_energy_checkins (date, energy_level, focus_level, mood_level)
            VALUES (?, ?, ?, ?)
            """,
            (date_value, energy, focus, mood),
        )
        row = conn.execute("SELECT * FROM daily_energy_checkins WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def get_plan(date_value: str | None = None) -> dict | None:
    ensure_day_planner_schema()
    date_value = _date(date_value)
    with get_connection() as conn:
        plan = conn.execute("SELECT * FROM daily_plans WHERE date = ?", (date_value,)).fetchone()
        if not plan:
            return None
        blocks = conn.execute(
            """
            SELECT *
            FROM daily_plan_blocks
            WHERE plan_id = ?
            ORDER BY start_time ASC, id ASC
            """,
            (plan["id"],),
        ).fetchall()
    return _plan_payload(dict(plan), [dict(row) for row in blocks])


def save_plan(date_value: str, plan_data: dict, blocks: list[dict], *, preserve_done: bool = False) -> dict:
    ensure_day_planner_schema()
    preserved: list[dict] = []
    with get_connection() as conn:
        current = conn.execute("SELECT * FROM daily_plans WHERE date = ?", (date_value,)).fetchone()
        if current and preserve_done:
            done_rows = conn.execute(
                """
                SELECT *
                FROM daily_plan_blocks
                WHERE plan_id = ? AND status = 'done'
                ORDER BY start_time ASC, id ASC
                """,
                (current["id"],),
            ).fetchall()
            preserved = [dict(row) for row in done_rows]
        conn.execute(
            """
            INSERT INTO daily_plans (
                date, mode, suggested_mode, energy_level, sleep_seconds,
                routine_score, status, message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                mode = excluded.mode,
                suggested_mode = excluded.suggested_mode,
                energy_level = excluded.energy_level,
                sleep_seconds = excluded.sleep_seconds,
                routine_score = excluded.routine_score,
                status = excluded.status,
                message = excluded.message,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                date_value,
                plan_data["mode"],
                plan_data.get("suggested_mode") or plan_data["mode"],
                plan_data["energy_level"],
                int(plan_data.get("sleep_seconds") or 0),
                float(plan_data.get("routine_score") or 0),
                plan_data.get("status") or "ready",
                plan_data.get("message") or "",
            ),
        )
        plan = conn.execute("SELECT * FROM daily_plans WHERE date = ?", (date_value,)).fetchone()
        plan_id = int(plan["id"])
        conn.execute("DELETE FROM daily_plan_blocks WHERE plan_id = ?", (plan_id,))
        for block in preserved + blocks:
            conn.execute(
                """
                INSERT INTO daily_plan_blocks (
                    plan_id, title, type, start_time, duration_minutes,
                    priority, status, linked_task_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_id,
                    block.get("title") or "Bloco",
                    block.get("type") or "task",
                    block.get("start_time") or "",
                    int(block.get("duration_minutes") or 25),
                    int(block.get("priority") or 3),
                    block.get("status") or "pending",
                    block.get("linked_task_id") or "",
                ),
            )
    return get_plan(date_value) or {}


def update_block_status(block_id: int, status: str) -> dict:
    ensure_day_planner_schema()
    clean_status = _clean_choice(status, {"pending", "active", "done", "skipped", "rescheduled"}, "pending")
    with get_connection() as conn:
        row = conn.execute("SELECT plan_id FROM daily_plan_blocks WHERE id = ?", (block_id,)).fetchone()
        if not row:
            raise ValueError("Bloco nao encontrado.")
        plan_id = int(row["plan_id"])
        if clean_status == "active":
            conn.execute(
                "UPDATE daily_plan_blocks SET status = 'pending', updated_at = CURRENT_TIMESTAMP WHERE plan_id = ? AND status = 'active'",
                (plan_id,),
            )
        conn.execute(
            "UPDATE daily_plan_blocks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (clean_status, block_id),
        )
        plan = conn.execute("SELECT * FROM daily_plans WHERE id = ?", (plan_id,)).fetchone()
        blocks = conn.execute(
            "SELECT * FROM daily_plan_blocks WHERE plan_id = ? ORDER BY start_time ASC, id ASC",
            (plan_id,),
        ).fetchall()
    return _plan_payload(dict(plan), [dict(row) for row in blocks])


def _plan_payload(plan: dict, blocks: list[dict]) -> dict:
    next_block = next((block for block in blocks if block["status"] == "active"), None)
    if not next_block:
        next_block = next((block for block in blocks if block["status"] == "pending"), None)
    return {
        "plan": plan,
        "blocks": blocks,
        "next_block": next_block,
        "completed_blocks": sum(1 for block in blocks if block["status"] == "done"),
        "total_blocks": len(blocks),
    }


def _date(value) -> str:
    return str(value or date.today().isoformat())[:10]


def _clean_choice(value, allowed: set[str], default: str) -> str:
    text = str(value or default).strip().lower()
    return text if text in allowed else default


DAY_PLANNER_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    mode TEXT NOT NULL DEFAULT 'normal',
    suggested_mode TEXT NOT NULL DEFAULT 'normal',
    energy_level TEXT NOT NULL DEFAULT 'media',
    sleep_seconds INTEGER NOT NULL DEFAULT 0,
    routine_score REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_plan_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'task',
    start_time TEXT NOT NULL DEFAULT '',
    duration_minutes INTEGER NOT NULL DEFAULT 25,
    priority INTEGER NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'pending',
    linked_task_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_id) REFERENCES daily_plans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_energy_checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    energy_level TEXT NOT NULL DEFAULT 'media',
    focus_level TEXT NOT NULL DEFAULT '',
    mood_level TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_plan_blocks_plan ON daily_plan_blocks(plan_id);
CREATE INDEX IF NOT EXISTS idx_daily_energy_checkins_date ON daily_energy_checkins(date);
"""

