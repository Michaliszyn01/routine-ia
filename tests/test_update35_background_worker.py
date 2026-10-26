from __future__ import annotations

from datetime import datetime, timedelta


def test_worker_status_file_reports_running_and_stale(client):
    from core.tools.background_worker.worker_controller import read_worker_status, write_worker_status

    write_worker_status({"monitoring": {"status": "active"}, "health_importer": {"running": True}})
    fresh = read_worker_status()

    assert fresh["running"] is True
    assert fresh["monitoring"]["status"] == "active"

    stale_time = (datetime.now() - timedelta(minutes=10)).isoformat(timespec="seconds")
    write_worker_status({"heartbeat_at": stale_time, "monitoring": {"status": "active"}})
    stale = read_worker_status()

    assert stale["running"] is False
    assert stale["stale"] is True


def test_monitoring_route_sets_worker_desired_state_in_testing(client):
    from backend import models
    from core.tools.monitoring.monitoring_service import stop_monitoring

    try:
        response = client.post("/api/monitoring-level1/start", json={"interval_seconds": 30})
        body = response.get_json()
        settings = models.get_settings()

        assert response.status_code == 200
        assert body["ok"] is True
        assert settings["auto_start_monitoring"] == "true"
        assert settings["monitoring_worker_state"] == "active"
        assert settings["monitoring_interval_seconds"] == "30"
    finally:
        stop_monitoring()


def test_health_page_has_simple_and_advanced_modes(client):
    response = client.get("/health")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "health-simple-view" in html
    assert "health-advanced-view" in html
    assert "health-advanced-area" in html
    assert "Registro manual legado" in html
