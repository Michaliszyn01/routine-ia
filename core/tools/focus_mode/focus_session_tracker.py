from __future__ import annotations

from datetime import datetime

from core.tools.monitoring.app_rules import classify_app
from core.tools.monitoring.monitoring_service import get_monitoring_status

from .focus_repository import add_app_usage
from .focus_rules import app_match_status


_last_seen: dict[int, datetime] = {}


def track_session_app(session: dict, focused_app: dict | None = None, *, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    session_id = int(session["id"])
    previous = _last_seen.get(session_id)
    _last_seen[session_id] = now
    seconds = int((now - previous).total_seconds()) if previous else 0
    seconds = max(0, min(seconds, 300))

    current = focused_app if focused_app is not None else _current_focused_app()
    app_name = _app_name(current)
    label = _label(current)
    rule = app_match_status(session.get("focus_type"), app_name, label)
    updated = session
    if session.get("status") == "active" and seconds:
        updated = add_app_usage(session_id, app_name, label, seconds, rule.match_status)
    return {
        "session": updated,
        "focused_app": {"app_name": app_name, "label": label, **(current or {})},
        "match": rule.__dict__,
        "observed_seconds": seconds,
        "alert": _alert_payload(updated, rule.match_status),
    }


def reset_session_tracking(session_id: int) -> None:
    _last_seen.pop(int(session_id), None)


def record_app_sample(session: dict, app_name: str, seconds: int, label: str | None = None) -> dict:
    classified = classify_app(app_name, app_name)
    clean_label = label or classified["label"]
    rule = app_match_status(session.get("focus_type"), app_name, clean_label)
    return add_app_usage(int(session["id"]), app_name, clean_label, int(seconds or 0), rule.match_status)


def _current_focused_app() -> dict | None:
    status = get_monitoring_status()
    focused = status.get("focused_app")
    if focused:
        return focused
    return None


def _app_name(focused_app: dict | None) -> str:
    if not focused_app:
        return "Desconhecido"
    classified = classify_app(focused_app.get("process_name"), focused_app.get("app_name"))
    return focused_app.get("app_name") or classified["app_name"]


def _label(focused_app: dict | None) -> str:
    if not focused_app:
        return "Neutro"
    if focused_app.get("label"):
        return focused_app["label"]
    return classify_app(focused_app.get("process_name"), focused_app.get("app_name"))["label"]


def _alert_payload(session: dict, match_status: str) -> dict | None:
    if match_status == "match":
        return None
    distracted = int(session.get("distracted_seconds") or 0)
    if distracted < 120:
        return None
    return {
        "message": "Voce saiu um pouco do bloco. Quer voltar para o projeto?",
        "actions": ["Voltar ao foco", "Ignorar por agora", "Pausar sessao"],
    }
