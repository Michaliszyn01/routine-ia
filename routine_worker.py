from __future__ import annotations

import signal
import time
from datetime import datetime

from backend import models
from backend.database import init_db
from core.tools.background_worker.worker_controller import mark_worker_stopped, write_worker_status
from core.tools.health_importer.health_scheduler import (
    get_health_import_scheduler_status,
    start_health_import_scheduler,
    stop_health_import_scheduler,
)
from core.tools.monitoring.monitoring_service import (
    get_monitoring_status,
    pause_monitoring,
    resume_monitoring,
    start_monitoring,
    stop_monitoring,
)


POLL_SECONDS = 5
_stop_requested = False


def main() -> None:
    init_db()
    _install_signal_handlers()
    last_health_interval = None
    try:
        while not _stop_requested:
            settings = models.get_settings()
            _sync_monitoring(settings)
            last_health_interval = _sync_health_importer(settings, last_health_interval)
            write_worker_status(
                {
                    "started_by": "routine_worker.py",
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                    "monitoring": get_monitoring_status(),
                    "health_importer": get_health_import_scheduler_status(),
                    "settings": {
                        "auto_start_monitoring": settings.get("auto_start_monitoring", "false"),
                        "monitoring_worker_state": settings.get("monitoring_worker_state", "off"),
                        "monitoring_interval_seconds": settings.get("monitoring_interval_seconds", "60"),
                        "health_auto_import_enabled": settings.get("health_auto_import_enabled", "true"),
                        "health_import_interval_hours": settings.get("health_import_interval_hours", "4"),
                    },
                }
            )
            time.sleep(POLL_SECONDS)
    finally:
        stop_monitoring()
        stop_health_import_scheduler()
        mark_worker_stopped("shutdown")


def _sync_monitoring(settings: dict) -> None:
    desired = settings.get("monitoring_worker_state") or "off"
    auto_enabled = str(settings.get("auto_start_monitoring", "false")).lower() == "true"
    interval = models.get_setting_int("monitoring_interval_seconds", 60)

    if auto_enabled and desired == "active":
        start_monitoring(interval)
        resume_monitoring()
        return
    if auto_enabled and desired == "paused":
        start_monitoring(interval)
        pause_monitoring()
        return
    stop_monitoring()


def _sync_health_importer(settings: dict, last_interval: str | None) -> str | None:
    enabled = str(settings.get("health_auto_import_enabled", "true")).lower() == "true"
    interval = str(settings.get("health_import_interval_hours", "4"))
    status = get_health_import_scheduler_status()

    if not enabled:
        stop_health_import_scheduler()
        return interval
    if status.get("running") and interval == last_interval:
        return interval
    if status.get("running"):
        stop_health_import_scheduler()
    start_health_import_scheduler()
    return interval


def _install_signal_handlers() -> None:
    def request_stop(signum, frame) -> None:
        del signum, frame
        global _stop_requested
        _stop_requested = True

    for signal_name in ("SIGINT", "SIGTERM"):
        signal_value = getattr(signal, signal_name, None)
        if signal_value is not None:
            signal.signal(signal_value, request_stop)


if __name__ == "__main__":
    main()
