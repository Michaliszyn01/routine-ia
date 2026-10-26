from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from backend import models
from backend.paths import get_app_data_dir, get_base_path, get_logs_dir, is_frozen


HEARTBEAT_STALE_SECONDS = 90
STATUS_FILE = "routine_worker_status.json"
LOG_FILE = "routine_worker.log"


def get_worker_status_path() -> Path:
    return get_app_data_dir() / STATUS_FILE


def get_worker_log_path() -> Path:
    return get_logs_dir() / LOG_FILE


def read_worker_status() -> dict:
    path = get_worker_status_path()
    if not path.exists():
        return _empty_status("status_missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_status("status_unreadable")

    heartbeat = _parse_time(payload.get("heartbeat_at"))
    stale = not heartbeat or datetime.now() - heartbeat > timedelta(seconds=HEARTBEAT_STALE_SECONDS)
    payload["running"] = not stale and payload.get("state") == "running"
    payload["stale"] = stale
    payload["status_path"] = str(path)
    payload["log_path"] = str(get_worker_log_path())
    return payload


def write_worker_status(payload: dict) -> None:
    data = {
        "state": "running",
        "pid": os.getpid(),
        "heartbeat_at": datetime.now().isoformat(timespec="seconds"),
        **payload,
    }
    path = get_worker_status_path()
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")


def mark_worker_stopped(reason: str = "stopped") -> None:
    current = read_worker_status()
    payload = {
        "state": "stopped",
        "pid": os.getpid(),
        "heartbeat_at": datetime.now().isoformat(timespec="seconds"),
        "running": False,
        "stale": False,
        "reason": reason,
        "monitoring": current.get("monitoring") or {},
        "health_importer": current.get("health_importer") or {},
    }
    get_worker_status_path().write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def ensure_background_worker() -> dict:
    settings = models.get_settings()
    if str(settings.get("background_worker_enabled", "true")).lower() != "true":
        return {"started": False, "enabled": False, "worker": read_worker_status()}

    status = read_worker_status()
    if status.get("running"):
        return {"started": False, "enabled": True, "worker": status}

    command = _worker_command()
    log_path = get_worker_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with open(log_path, "a", encoding="utf-8") as log_file:
        subprocess.Popen(
            command,
            cwd=str(get_base_path()),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=log_file,
            close_fds=False,
            creationflags=creationflags,
        )
    return {"started": True, "enabled": True, "worker": read_worker_status(), "command": _safe_command(command)}


def get_background_worker_overview() -> dict:
    settings = models.get_settings()
    status = read_worker_status()
    return {
        "enabled": str(settings.get("background_worker_enabled", "true")).lower() == "true",
        "desired_monitoring_state": settings.get("monitoring_worker_state", "off"),
        "auto_start_monitoring": settings.get("auto_start_monitoring", "false"),
        "health_auto_import_enabled": settings.get("health_auto_import_enabled", "true"),
        "worker": status,
    }


def _worker_command() -> list[str]:
    if is_frozen():
        return [sys.executable, "--worker"]
    return [sys.executable, str(get_base_path() / "routine_worker.py")]


def _safe_command(command: list[str]) -> list[str]:
    return [Path(item).name if index == 0 else item for index, item in enumerate(command)]


def _empty_status(reason: str) -> dict:
    return {
        "state": "missing",
        "running": False,
        "stale": True,
        "reason": reason,
        "status_path": str(get_worker_status_path()),
        "log_path": str(get_worker_log_path()),
    }


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
