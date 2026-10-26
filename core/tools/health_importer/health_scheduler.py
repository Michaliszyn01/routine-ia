from __future__ import annotations

import threading
from datetime import datetime, timedelta

from backend import models

from .health_service import run_health_import


_lock = threading.RLock()
_thread: threading.Thread | None = None
_stop_event = threading.Event()
_last_result: dict | None = None
_last_error = ""
_next_run_at = ""


def start_health_import_scheduler() -> dict:
    global _thread, _last_error
    with _lock:
        if _thread and _thread.is_alive():
            return get_health_import_scheduler_status()
        _stop_event.clear()
        _last_error = ""
        _thread = threading.Thread(target=_scheduler_loop, name="RoutineIAHealthImporter", daemon=True)
        _thread.start()
    return get_health_import_scheduler_status()


def stop_health_import_scheduler() -> dict:
    global _thread, _next_run_at
    with _lock:
        _stop_event.set()
        thread = _thread
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=2)
    with _lock:
        _thread = None
        _next_run_at = ""
    return get_health_import_scheduler_status()


def get_health_import_scheduler_status() -> dict:
    with _lock:
        running = bool(_thread and _thread.is_alive())
        return {
            "running": running,
            "next_run_at": _next_run_at if running else "",
            "last_result": dict(_last_result) if _last_result else None,
            "last_error": _last_error,
        }


def _scheduler_loop() -> None:
    global _last_result, _last_error, _next_run_at
    first_cycle = True
    while not _stop_event.is_set():
        settings = models.get_settings()
        enabled = str(settings.get("health_auto_import_enabled", "true")).lower() == "true"
        interval_hours = _interval_hours(settings.get("health_import_interval_hours"))
        wait_seconds = interval_hours * 3600
        if enabled and first_cycle:
            _run_import_once()
        with _lock:
            _next_run_at = (datetime.now() + timedelta(seconds=wait_seconds)).isoformat(timespec="seconds") if enabled else ""
        first_cycle = False
        if _stop_event.wait(wait_seconds):
            break
        if not enabled:
            continue
        _run_import_once()


def _run_import_once() -> None:
    global _last_result, _last_error
    try:
        result = run_health_import()
        with _lock:
            _last_result = result
            _last_error = "" if result.get("ok") else result.get("message", "")
    except Exception as exc:
        with _lock:
            _last_error = str(exc)[:500]


def _interval_hours(value) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        parsed = 4
    return min(24, max(1, parsed))
