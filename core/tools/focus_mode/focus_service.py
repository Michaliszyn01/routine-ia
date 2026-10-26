from __future__ import annotations

from datetime import date, timedelta

from core.tools.day_planner.planner_repository import update_block_status

from . import focus_repository as repo
from .focus_rules import expected_apps_for, focus_type_from_block, legacy_category_for_focus_type, normalize_focus_type
from .focus_session_tracker import record_app_sample, reset_session_tracking, track_session_app


def start_focus_session_v5(payload: dict | None = None) -> dict:
    payload = payload or {}
    block = None
    block_id = _int(payload.get("plan_block_id") or payload.get("block_id"))
    if block_id:
        block = repo.get_plan_block(block_id)
        if not block:
            raise ValueError("Bloco do plano nao encontrado.")

    focus_type = normalize_focus_type(payload.get("focus_type") or payload.get("type") or focus_type_from_block(block))
    title = _text(payload.get("title") or (block or {}).get("title") or "Foco rapido", 160)
    planned_minutes = _bounded_int(payload.get("planned_minutes") or payload.get("duration_minutes") or (block or {}).get("duration_minutes"), 1, 720, 25)
    data = {
        "date": _date(payload.get("date") or (block or {}).get("date")),
        "plan_block_id": block_id or None,
        "title": title,
        "focus_type": focus_type,
        "planned_minutes": planned_minutes,
        "break_minutes": _bounded_int(payload.get("break_minutes"), 0, 120, 0),
        "next_step": _text(payload.get("next_step") or payload.get("note") or _next_step_for(focus_type), 1000),
        "project_id": payload.get("project_id") or None,
        "category": legacy_category_for_focus_type(focus_type),
        "source": "plan_block" if block_id else "quick_focus",
    }
    session = repo.create_session(data)
    if block_id:
        update_block_status(block_id, "active")
    return _decorate_session(session)


def pause_focus_session(payload: dict | None = None) -> dict:
    session = _session_from_payload(payload)
    reset_session_tracking(int(session["id"]))
    return _decorate_session(repo.update_status(int(session["id"]), "paused", "paused"))


def resume_focus_session(payload: dict | None = None) -> dict:
    session = _session_from_payload(payload)
    return _decorate_session(repo.update_status(int(session["id"]), "active", "resumed"))


def complete_focus_session_v5(payload: dict | None = None) -> dict:
    payload = payload or {}
    session = _session_from_payload(payload)
    reset_session_tracking(int(session["id"]))
    finished = repo.finish_session(int(session["id"]), "completed", _text(payload.get("completion_note") or payload.get("note"), 1000), _int(payload.get("actual_seconds")))
    if finished.get("plan_block_id"):
        update_block_status(int(finished["plan_block_id"]), "done")
    return _decorate_session(finished)


def abandon_focus_session(payload: dict | None = None) -> dict:
    payload = payload or {}
    session = _session_from_payload(payload)
    reset_session_tracking(int(session["id"]))
    finished = repo.finish_session(int(session["id"]), "abandoned", _text(payload.get("completion_note") or payload.get("note"), 1000), _int(payload.get("actual_seconds")))
    block_status = str(payload.get("block_status") or "pending").strip().lower()
    if finished.get("plan_block_id") and block_status in {"pending", "skipped", "rescheduled"}:
        update_block_status(int(finished["plan_block_id"]), block_status)
    return _decorate_session(finished)


def get_current_focus_session() -> dict:
    session = repo.active_session()
    if not session:
        return {"ok": True, "active": False, "session": None}
    tracked = track_session_app(session)
    tracked["session"] = _decorate_session(tracked["session"])
    return {"ok": True, "active": True, **tracked}


def get_focus_session(session_id: int) -> dict:
    session = repo.get_session(session_id)
    if not session:
        raise ValueError("Sessao de foco nao encontrada.")
    return {"ok": True, "session": _decorate_session(session)}


def get_focus_history(days: int = 7) -> dict:
    days = max(1, min(int(days or 7), 90))
    end = date.today()
    start = end - timedelta(days=days - 1)
    sessions = [_decorate_session(item) for item in repo.list_sessions(start.isoformat(), end.isoformat())]
    return {"ok": True, "days": days, "start_date": start.isoformat(), "end_date": end.isoformat(), "sessions": sessions}


def get_focus_summary_today(date_value: str | None = None) -> dict:
    target = _date(date_value)
    return {"ok": True, "date": target, "summary": repo.summary(target, target), "top_focus_breakers": repo.top_breakers(target, target)}


def get_focus_summary_range(start: str, end: str) -> dict:
    return repo.summary(start, end)


def record_focus_app_sample(session_id: int, app_name: str, seconds: int, label: str | None = None) -> dict:
    session = repo.get_session(session_id)
    if not session:
        raise ValueError("Sessao de foco nao encontrada.")
    return _decorate_session(record_app_sample(session, app_name, seconds, label))


def _decorate_session(session: dict) -> dict:
    focus_type = normalize_focus_type(session.get("focus_type"))
    return {
        **session,
        "focus_type": focus_type,
        "expected_apps": expected_apps_for(focus_type),
        "focused_minutes": round(int(session.get("focused_seconds") or 0) / 60, 1),
        "distracted_minutes": round(int(session.get("distracted_seconds") or 0) / 60, 1),
        "actual_minutes": round(int(session.get("actual_seconds") or 0) / 60, 1),
    }


def _session_from_payload(payload: dict | None) -> dict:
    payload = payload or {}
    session_id = _int(payload.get("session_id") or payload.get("id"))
    if session_id:
        session = repo.get_session(session_id)
        if not session:
            raise ValueError("Sessao de foco nao encontrada.")
        return session
    session = repo.active_session()
    if not session:
        raise ValueError("Nenhuma sessao de foco ativa.")
    return session


def _next_step_for(focus_type: str) -> str:
    return {
        "study": "Abrir o material e resolver o primeiro item pequeno.",
        "project": "Abrir o projeto e escolher uma pequena correcao.",
        "workout": "Comecar pelo aquecimento ou primeiro exercicio.",
        "organization": "Escolher uma area pequena para organizar.",
        "reading": "Abrir o texto e ler a primeira pagina.",
        "rest": "Descansar sem transformar a pausa em outra tarefa.",
    }.get(focus_type, "Escolher o menor proximo passo.")


def _date(value) -> str:
    return str(value or date.today().isoformat())[:10]


def _int(value, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _bounded_int(value, minimum: int, maximum: int, default: int) -> int:
    return min(max(_int(value, default), minimum), maximum)


def _text(value, limit: int) -> str:
    return str(value or "").strip()[:limit]
