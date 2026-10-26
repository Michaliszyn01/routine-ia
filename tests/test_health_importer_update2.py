from __future__ import annotations

import csv
from pathlib import Path


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_scanner_finds_health_sync_folders_and_ignores_fit_tcx(tmp_path):
    from core.tools.health_importer.health_file_scanner import scan_health_sync_files

    sleep_dir = tmp_path / "Health Sync Dormir"
    activities_dir = tmp_path / "Health Sync Atividades"
    sleep_dir.mkdir()
    activities_dir.mkdir()
    (sleep_dir / "sono.csv").write_text("Data,Hora,Duração em segundos,Fase do sono\n", encoding="utf-8")
    (activities_dir / "atividade.fit").write_text("ignored", encoding="utf-8")
    (activities_dir / "atividade.tcx").write_text("ignored", encoding="utf-8")
    (activities_dir / "atividade.csv").write_text("Data,Hora,Tempo ativo\n", encoding="utf-8")

    result = scan_health_sync_files(tmp_path)

    assert result["exists"] is True
    assert {item.data_type for item in result["candidates"]} == {"sleep", "activities"}
    assert len(result["ignored"]) == 2


def test_sleep_parser_sums_sleep_stages(tmp_path):
    from core.tools.health_importer.health_csv_parser import parse_sleep_csv

    path = tmp_path / "sleep.csv"
    write_csv(
        path,
        ["Data", "Hora", "Duração em segundos", "Fase do sono"],
        [
            {"Data": "2026-06-30", "Hora": "01:00:00", "Duração em segundos": "3600", "Fase do sono": "light"},
            {"Data": "2026-06-30", "Hora": "02:00:00", "Duração em segundos": "1800", "Fase do sono": "deep"},
            {"Data": "2026-06-30", "Hora": "03:00:00", "Duração em segundos": "900", "Fase do sono": "rem"},
            {"Data": "2026-06-30", "Hora": "04:00:00", "Duração em segundos": "300", "Fase do sono": "awake"},
        ],
    )

    parsed = parse_sleep_csv(path)
    summary = parsed["summaries"][0]

    assert parsed["errors"] == []
    assert summary.total_sleep_seconds == 6300
    assert summary.light_sleep_seconds == 3600
    assert summary.deep_sleep_seconds == 1800
    assert summary.rem_sleep_seconds == 900
    assert summary.awake_seconds == 300


def test_steps_parser_sums_daily_steps(tmp_path):
    from core.tools.health_importer.health_csv_parser import parse_steps_csv

    path = tmp_path / "steps.csv"
    write_csv(
        path,
        ["Data", "Hora", "Passos"],
        [
            {"Data": "30/06/2026", "Hora": "08:00:00", "Passos": "1200"},
            {"Data": "30/06/2026", "Hora": "09:00:00", "Passos": "800"},
        ],
    )

    parsed = parse_steps_csv(path)

    assert parsed["summaries"][0].total_steps == 2000


def test_activities_parser_reads_csv_rows(tmp_path):
    from core.tools.health_importer.health_csv_parser import parse_activities_csv

    path = tmp_path / "activities.csv"
    write_csv(
        path,
        ["Aplicação de origem", "Tipo de atividade", "Nome da atividade", "Data", "Hora", "Tempo decorrido", "Tempo ativo", "Distância (km)"],
        [
            {
                "Aplicação de origem": "Samsung Health",
                "Tipo de atividade": "corrida",
                "Nome da atividade": "Corrida leve",
                "Data": "2026.06.30",
                "Hora": "18:30:00",
                "Tempo decorrido": "00:40:00",
                "Tempo ativo": "00:35:00",
                "Distância (km)": "5,2",
            }
        ],
    )

    parsed = parse_activities_csv(path)
    record = parsed["records"][0]

    assert record.activity_type == "corrida"
    assert record.elapsed_seconds == 2400
    assert record.active_seconds == 2100
    assert record.distance_km == 5.2


def test_heart_rate_parser_generates_daily_summary(tmp_path):
    from core.tools.health_importer.health_csv_parser import parse_heart_rate_csv

    path = tmp_path / "hr.csv"
    write_csv(
        path,
        ["Data", "Hora", "Frequência Cardíaca", "Origem"],
        [
            {"Data": "2026-06-30", "Hora": "08:00:00", "Frequência Cardíaca": "60", "Origem": "watch"},
            {"Data": "2026-06-30", "Hora": "08:01:00", "Frequência Cardíaca": "80", "Origem": "watch"},
            {"Data": "2026-06-30", "Hora": "08:02:00", "Frequência Cardíaca": "100", "Origem": "watch"},
        ],
    )

    parsed = parse_heart_rate_csv(path)
    summary = parsed["summaries"][0]

    assert summary.avg_bpm == 80
    assert summary.min_bpm == 60
    assert summary.max_bpm == 100
    assert summary.samples_count == 3


def test_import_deduplicates_overlapping_steps_files(tmp_path, flask_app):
    from core.tools.health_importer.health_repository import health_dashboard
    from core.tools.health_importer.health_service import run_health_import

    steps_dir = tmp_path / "Health Sync Passos"
    write_csv(
        steps_dir / "Passos 2026.06.30.csv",
        ["Data", "Hora", "Passos"],
        [{"Data": "2026-06-30", "Hora": "08:00:00", "Passos": "1000"}],
    )
    write_csv(
        steps_dir / "Passos 2026.06.29-2026.06.30.csv",
        ["Data", "Hora", "Passos"],
        [
            {"Data": "2026-06-30", "Hora": "08:00:00", "Passos": "1000"},
            {"Data": "2026-06-30", "Hora": "09:00:00", "Passos": "500"},
        ],
    )

    first = run_health_import(str(tmp_path))
    second = run_health_import(str(tmp_path))
    dashboard = health_dashboard("2026-06-30")
    today = next(row for row in dashboard["daily"] if row["date"] == "2026-06-30")

    assert first["imported_rows"] == 2
    assert second["skipped_files"] == 2
    assert today["steps"] == 1500


def test_import_does_not_break_when_folder_is_missing(tmp_path, flask_app):
    from core.tools.health_importer.health_service import run_health_import

    result = run_health_import(str(tmp_path))

    assert result["status"] == "success"
    assert result["imported_rows"] == 0


def test_import_lock_prevents_parallel_imports():
    from core.tools.health_importer import health_service

    assert health_service._import_lock.acquire(blocking=False)
    try:
        result = health_service.run_health_import()
    finally:
        health_service._import_lock.release()

    assert result["status"] == "busy"


def test_health_status_api_returns_base_path_and_last_import(tmp_path, client):
    from core.tools.health_importer.health_repository import record_imported_file

    response = client.post(
        "/api/health/settings",
        json={"health_sync_base_path": str(tmp_path), "health_auto_import_enabled": False},
    )
    assert response.status_code == 200

    record_imported_file(
        file_path=str(tmp_path / "sono.csv"),
        file_hash="status-api-hash",
        data_type="sleep",
        rows_imported=3,
        status="success",
    )

    status = client.get("/api/health/status").get_json()

    assert status["settings"]["health_sync_base_path"] == str(tmp_path)
    assert status["scan"]["exists"] is True
    assert status["last_import"]["file_name"] == "sono.csv"
    assert status["import_stats"]["total"] >= 1
    assert status["operation"]["folder_ready"] is True
    assert status["operation"]["auto_import_enabled"] is False
    assert status["operation"]["code"] == "auto_disabled"


def test_health_summary_today_returns_sleep_steps_workout_and_heart_rate(client):
    from core.tools.health_importer.health_repository import (
        save_activity_records,
        save_heart_rate_summaries,
        save_sleep_records,
        save_steps_records,
    )
    from core.tools.health_importer.health_schemas import (
        ActivityRecord,
        DailyHeartRateSummary,
        SleepStageRecord,
        StepsRecord,
    )

    save_sleep_records(
        [
            SleepStageRecord("2026-07-01", "01:00:00", 18000, "light", "sleep.csv"),
            SleepStageRecord("2026-07-01", "06:00:00", 4800, "deep", "sleep.csv"),
            SleepStageRecord("2026-07-01", "07:20:00", 6200, "rem", "sleep.csv"),
            SleepStageRecord("2026-07-01", "09:03:20", 600, "awake", "sleep.csv"),
        ]
    )
    save_steps_records([StepsRecord("2026-07-01", "12:00:00", 6430, "steps.csv")])
    save_activity_records(
        [
            ActivityRecord("2026-07-01", "17:17:00", "treino", "Musculacao", 2820, 2820, 0, "activities.csv")
        ]
    )
    save_heart_rate_summaries([DailyHeartRateSummary("2026-07-01", 78, 52, 142, 1240)])

    payload = client.get("/api/health/summary/today?date=2026-07-01").get_json()["data"]

    assert payload["sleep"]["total_sleep_seconds"] == 29000
    assert payload["steps_summary"]["total_steps"] == 6430
    assert payload["workout"]["label"] == "Musculacao"
    assert payload["heart_rate"]["avg_bpm"] == 78
    assert payload["heart_rate"]["samples_count"] == 1240


def test_health_last_7_days_returns_days_with_missing_data(client):
    payload = client.get("/api/health/summary/last-7-days?date=2026-07-01").get_json()["data"]

    assert len(payload) == 7
    assert payload[0]["date"] == "2026-07-01"
    assert payload[-1]["date"] == "2026-06-25"
    assert any(day["sleep"]["has_data"] is False for day in payload)


def test_health_import_now_api_calls_import_service(client, monkeypatch, tmp_path):
    import app as app_module

    called = {}

    def fake_run_health_import(base_path=None):
        called["base_path"] = base_path
        return {"ok": True, "status": "success", "message": "Importacao concluida com sucesso."}

    monkeypatch.setattr(app_module, "run_health_import", fake_run_health_import)

    response = client.post("/api/health/import-now", json={"health_sync_base_path": str(tmp_path)})

    assert response.status_code == 200
    assert response.get_json()["message"] == "Importacao concluida com sucesso."
    assert called["base_path"] == str(tmp_path)


def test_health_settings_rejects_missing_folder(client, tmp_path):
    missing = tmp_path / "nao-existe"

    response = client.post("/api/health/settings", json={"health_sync_base_path": str(missing)})

    assert response.status_code == 400
    assert "Pasta nao encontrada" in response.get_json()["error"]


def test_health_js_declares_update_2_2_formatters():
    script = Path("frontend/static/js/health.js").read_text(encoding="utf-8")

    assert "function formatSecondsToHoursMinutes" in script
    assert "function formatNumber" in script
    assert "function formatDateBR" in script
    assert "function formatBpm" in script
    assert "function formatDistanceKm" in script
    assert "function renderHealthOperation" in script


def test_health_page_has_operational_diagnostic(client):
    response = client.get("/health")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "health-operation-card" in html
    assert "health-operation-title" in html
