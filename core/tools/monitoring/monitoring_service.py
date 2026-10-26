from __future__ import annotations

import threading
import time
from datetime import datetime

from .monitoring_repository import daily_summary, delete_usage_data, save_increments, weekly_summary
from .process_scanner import scan_open_apps
from .usage_tracker import DEFAULT_INTERVAL_SECONDS, UsageTracker, normalize_interval
from .window_scanner import get_focused_app, normalize_focused_app


_lock = threading.RLock()
_thread: threading.Thread | None = None
_stop_event = threading.Event()
_status = "off"
_last_scan_at = ""
_last_saved_at = ""
_last_error = ""
_last_open_apps: list[dict] = []
_last_focused_app: dict | None = None
_interval_seconds = DEFAULT_INTERVAL_SECONDS


def start_monitoring(interval_seconds: int | None = None) -> dict:
    global _thread, _status, _interval_seconds, _last_error
    with _lock:
        _interval_seconds = normalize_interval(interval_seconds or _interval_seconds)
        if _thread and _thread.is_alive():
            _status = "active"
            return get_monitoring_status()
        _stop_event.clear()
        _status = "starting"
        _last_error = ""
        _thread = threading.Thread(target=_monitor_loop, name="RoutineIALevel1Monitoring", daemon=True)
        _thread.start()
    return get_monitoring_status()


def pause_monitoring() -> dict:
    global _status
    with _lock:
        if _status in {"active", "starting"}:
            _status = "paused"
    return get_monitoring_status()


def resume_monitoring() -> dict:
    global _status
    with _lock:
        if _thread and _thread.is_alive():
            _status = "active"
            return get_monitoring_status()
    return start_monitoring()


def stop_monitoring() -> dict:
    global _thread, _status
    with _lock:
        _stop_event.set()
        thread = _thread
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=2)
    with _lock:
        _thread = None
        _status = "off"
    return get_monitoring_status()


def run_monitoring_tick(
    window_iter=None,
    focused_app: dict | None = None,
    interval_seconds: int | None = None,
) -> dict:
    global _last_scan_at, _last_saved_at, _last_error, _last_open_apps, _last_focused_app
    seconds = normalize_interval(interval_seconds or _interval_seconds)
    try:
        apps = scan_open_apps(window_iter)
        current_focus = normalize_focused_app(focused_app) if focused_app is not None else get_focused_app()
        tracker = UsageTracker(seconds)
        increments = tracker.calculate_focus_increment(current_focus, seconds)
        saved = save_increments(increments)
        now = datetime.now().isoformat(timespec="seconds")
        with _lock:
            _last_scan_at = now
            _last_saved_at = now if saved else _last_saved_at
            _last_open_apps = apps
            _last_focused_app = current_focus
            _last_error = ""
        return {
            "ok": True,
            "interval_seconds": seconds,
            "focused_app": current_focus,
            "open_apps": apps,
            "saved": saved,
            "summary": daily_summary(),
        }
    except Exception as exc:
        with _lock:
            _last_error = str(exc)[:500]
        return {"ok": False, "error": _last_error, "summary": daily_summary()}


def get_today_summary(target_date: str | None = None) -> dict:
    return daily_summary(target_date)


def get_week_summary(reference_date: str | None = None) -> dict:
    return weekly_summary(reference_date)


def delete_monitoring_data(scope: str = "today") -> dict:
    return delete_usage_data(scope)


def get_monitoring_status() -> dict:
    with _lock:
        running = bool(_thread and _thread.is_alive())
        status = _status if running or _status == "paused" else "off"
        return {
            "status": status,
            "running": running,
            "thread_alive": running,
            "interval_seconds": _interval_seconds,
            "last_scan_at": _last_scan_at,
            "last_saved_at": _last_saved_at,
            "last_error": _last_error,
            "focused_app": dict(_last_focused_app) if _last_focused_app else None,
            "open_apps": list(_last_open_apps),
            "open_apps_count": len(_last_open_apps),
            "privacy": {
                "local_only": True,
                "captures": ["focused_process_name", "focused_app_name", "focused_window_title", "label", "visible_app_context"],
                "does_not_capture": ["screenshots", "typed_keys", "browser_tabs", "screen_contents"],
            },
        }


def _monitor_loop() -> None:
    global _status
    with _lock:
        _status = "active"
    while not _stop_event.is_set():
        with _lock:
            status = _status
            seconds = _interval_seconds
        if status == "paused":
            time.sleep(1)
            continue
        run_monitoring_tick(interval_seconds=seconds)
        _stop_event.wait(seconds)
    with _lock:
        if _status != "off":
            _status = "off"
