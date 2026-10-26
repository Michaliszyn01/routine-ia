from __future__ import annotations

from backend.database import get_connection
from backend.projects import list_projects


def pending_tasks_for_day(date_value: str) -> list[dict]:
    tasks = _weekly_items(date_value)
    if tasks:
        return sorted(tasks, key=_priority_key)
    return _fallback_tasks()


def microsteps_for_block(block_type: str, title: str) -> list[str]:
    text = f"{block_type} {title}".lower()
    if "estud" in text or "enem" in text or "matemat" in text:
        return ["Abrir material", "Fazer 5 questoes", "Corrigir erros"]
    if "program" in text or "projeto" in text or "routine" in text:
        return ["Abrir projeto", "Escolher pequena tarefa", "Implementar", "Testar"]
    if "treino" in text or "academia" in text:
        return ["Trocar roupa", "Iniciar treino", "Registrar treino"]
    return ["Abrir contexto", "Escolher menor parte", "Fazer por 5 minutos"]


def _weekly_items(date_value: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, category, estimated_minutes, linked_project_id, completed
            FROM weekly_plan_items
            WHERE date = ? AND completed = 0
            ORDER BY estimated_minutes ASC, id ASC
            """,
            (date_value,),
        ).fetchall()
    return [
        {
            "title": row["title"] or "Tarefa do planejamento",
            "type": _type_for(row["category"], row["title"]),
            "duration_minutes": int(row["estimated_minutes"] or 25),
            "priority": _priority_for(row["category"], row["title"]),
            "linked_task_id": f"weekly:{row['id']}",
        }
        for row in rows
    ]


def _fallback_tasks() -> list[dict]:
    projects = list_projects()
    project_title = projects[0]["name"] if projects else "Projeto"
    return [
        {"title": project_title, "type": "project", "duration_minutes": 50, "priority": 1, "linked_task_id": ""},
        {"title": "Estudo", "type": "study", "duration_minutes": 25, "priority": 2, "linked_task_id": ""},
        {"title": "Treino", "type": "workout", "duration_minutes": 45, "priority": 3, "linked_task_id": ""},
        {"title": "Organizacao", "type": "admin", "duration_minutes": 15, "priority": 4, "linked_task_id": ""},
        {"title": "Descanso", "type": "break", "duration_minutes": 10, "priority": 5, "linked_task_id": ""},
    ]


def _priority_key(task: dict) -> tuple:
    return (int(task.get("priority") or 5), int(task.get("duration_minutes") or 999), task.get("title") or "")


def _priority_for(category: str, title: str) -> int:
    text = f"{category} {title}".lower()
    if "atras" in text or "urg" in text or "prazo" in text:
        return 1
    if "projeto" in text or "program" in text:
        return 2
    if "estud" in text or "enem" in text:
        return 2
    if "pequen" in text or "rapido" in text:
        return 3
    return 4


def _type_for(category: str, title: str) -> str:
    text = f"{category} {title}".lower()
    if "treino" in text or "academia" in text:
        return "workout"
    if "estud" in text or "enem" in text:
        return "study"
    if "program" in text or "projeto" in text:
        return "project"
    return "task"

