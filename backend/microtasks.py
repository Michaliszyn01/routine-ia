from __future__ import annotations

from datetime import date

from .database import get_connection
from .validators import bounded_int, bool_to_int, sanitize_text, validate_date


def list_microtasks(date_value: str | None = None) -> dict:
    date_value = validate_date(date_value or date.today().isoformat())
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM microtasks
            WHERE date = ?
            ORDER BY completed ASC, order_index ASC, id ASC
            """,
            (date_value,),
        ).fetchall()
    tasks = [dict(row) for row in rows]
    return {
        "date": date_value,
        "microtasks": tasks,
        "completed": sum(1 for task in tasks if int(task.get("completed") or 0)),
        "total": len(tasks),
    }


def generate_microtasks(payload: dict) -> dict:
    date_value = validate_date(payload.get("date") or date.today().isoformat())
    title = sanitize_text(payload.get("title") or payload.get("action") or "Comecar pequeno", 160)
    category = sanitize_text(payload.get("category") or "rotina", 60)
    source_type = sanitize_text(payload.get("source_type") or "command_center", 60)
    source_id = sanitize_text(payload.get("source_id"), 80)
    steps = payload.get("microsteps") or payload.get("steps") or _steps_for(title, category)
    if not isinstance(steps, list):
        steps = _steps_for(title, category)
    clean_steps = []
    for index, raw_step in enumerate(steps[:5]):
        if isinstance(raw_step, dict):
            step_title = sanitize_text(raw_step.get("title"), 160)
            description = sanitize_text(raw_step.get("description"), 300)
            minutes = bounded_int(raw_step.get("estimated_minutes"), "estimated_minutes", "Minutos", minimum=1, maximum=30, default=2)
        else:
            step_title = sanitize_text(raw_step, 160)
            description = ""
            minutes = 1 if index == 0 else 2
        if step_title:
            clean_steps.append((step_title, description, minutes, index))
    if not clean_steps:
        clean_steps = [(step, "", 1 if index == 0 else 2, index) for index, step in enumerate(_steps_for(title, category))]

    with get_connection() as conn:
        conn.execute(
            "DELETE FROM microtasks WHERE date = ? AND source_type = ? AND COALESCE(source_id, '') = ?",
            (date_value, source_type, source_id or ""),
        )
        for step_title, description, minutes, index in clean_steps:
            conn.execute(
                """
                INSERT INTO microtasks (
                    date, source_type, source_id, title, description,
                    estimated_minutes, completed, order_index
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (date_value, source_type, source_id, step_title, description, minutes, index),
            )
    return list_microtasks(date_value)


def toggle_microtask(payload: dict) -> dict:
    task_id = bounded_int(payload.get("id") or payload.get("microtask_id"), "id", "Microtarefa", minimum=1)
    completed = bool_to_int(payload.get("completed", True))
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE microtasks
            SET completed = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (completed, task_id),
        )
        row = conn.execute("SELECT * FROM microtasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise ValueError("Microtarefa nao encontrada.")
    return {"microtask": dict(row), "feedback": "Microtarefa concluida. Proximo passo desbloqueado." if completed else "Microtarefa reaberta."}


def microtask_summary(start: str, end: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed
            FROM microtasks
            WHERE date >= ? AND date <= ?
            """,
            (start, end),
        ).fetchone()
    return {
        "total": int(row["total"] or 0),
        "completed": int(row["completed"] or 0),
    }


def _steps_for(title: str, category: str) -> list[str]:
    text = f"{title} {category}".lower()
    if "matemat" in text or "estud" in text or "enem" in text:
        return ["Abrir material", "Escolher 1 exercicio", "Fazer por 5 minutos", "Marcar dificuldade", "Decidir se continua"]
    if "program" in text or "projeto" in text or "codigo" in text or "code" in text:
        return ["Abrir VS Code", "Abrir o projeto", "Escolher uma tarefa pequena", "Alterar um arquivo", "Rodar app ou teste"]
    if "sono" in text or "dorm" in text:
        return ["Salvar o dia", "Separar agua", "Desligar distracoes", "Preparar cama", "Fechar sem culpa"]
    if "saude" in text or "treino" in text:
        return ["Beber agua", "Separar roupa ou tenis", "Fazer 3 minutos leves", "Registrar energia", "Parar ou continuar"]
    return ["Abrir o contexto", "Escolher uma parte pequena", "Fazer por 5 minutos", "Marcar como iniciado", "Salvar o minimo"]
