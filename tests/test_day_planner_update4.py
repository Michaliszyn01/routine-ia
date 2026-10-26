from __future__ import annotations

from backend.database import get_connection
from core.tools.health_importer.health_repository import save_sleep_records
from core.tools.health_importer.health_schemas import SleepStageRecord


def test_generate_basic_plan_without_health_data(client):
    _clear_day("2026-07-10")

    response = client.post("/api/day-planner/generate", json={"date": "2026-07-10", "energy_level": "media"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["plan"]["plan"]["mode"] == "normal"
    assert payload["next_step"]["title"]
    assert payload["plan"]["blocks"]


def test_generate_light_day_with_low_energy(client):
    _clear_day("2026-07-11")

    payload = client.post("/api/day-planner/generate", json={"date": "2026-07-11", "energy_level": "baixa"}).get_json()

    assert payload["plan"]["plan"]["mode"] == "light"
    assert max(block["duration_minutes"] for block in payload["plan"]["blocks"] if block["type"] != "break") <= 25


def test_generate_normal_day_with_medium_energy(client):
    _clear_day("2026-07-12")

    payload = client.post("/api/day-planner/generate", json={"date": "2026-07-12", "energy_level": "media"}).get_json()

    assert payload["plan"]["plan"]["mode"] == "normal"


def test_generate_strong_day_with_high_energy_and_good_sleep(client):
    _clear_day("2026-07-13")
    save_sleep_records([SleepStageRecord("2026-07-13", "00:00:00", 8 * 3600, "light", "sleep.csv")])

    payload = client.post("/api/day-planner/generate", json={"date": "2026-07-13", "energy_level": "alta"}).get_json()

    assert payload["plan"]["plan"]["mode"] == "strong"
    assert any(block["duration_minutes"] == 50 for block in payload["plan"]["blocks"])


def test_sleep_under_six_hours_reduces_plan_load(client):
    _clear_day("2026-07-14")
    save_sleep_records([SleepStageRecord("2026-07-14", "00:00:00", 5 * 3600, "light", "sleep.csv")])

    payload = client.post("/api/day-planner/generate", json={"date": "2026-07-14", "energy_level": "alta"}).get_json()

    assert payload["plan"]["plan"]["mode"] == "light"
    assert "Sono abaixo de 6h" in payload["context"]["mode_reason"]


def test_replan_keeps_completed_blocks(client):
    _clear_day("2026-07-15")
    plan = client.post("/api/day-planner/generate", json={"date": "2026-07-15", "energy_level": "media"}).get_json()
    first_block = plan["next_step"]
    client.post("/api/day-planner/block/complete", json={"block_id": first_block["id"]})

    replanned = client.post("/api/day-planner/replan", json={"date": "2026-07-15"}).get_json()

    done_blocks = [block for block in replanned["plan"]["blocks"] if block["status"] == "done"]
    assert len(done_blocks) == 1
    assert done_blocks[0]["title"] == first_block["title"]
    assert replanned["plan"]["plan"]["status"] == "adjusted"


def test_complete_and_skip_block_change_status(client):
    _clear_day("2026-07-16")
    plan = client.post("/api/day-planner/generate", json={"date": "2026-07-16", "energy_level": "media"}).get_json()
    first_block = plan["next_step"]
    completed = client.post("/api/day-planner/block/complete", json={"block_id": first_block["id"]}).get_json()
    next_block = completed["plan"]["next_block"]
    skipped = client.post("/api/day-planner/block/skip", json={"block_id": next_block["id"]}).get_json()

    statuses = {block["id"]: block["status"] for block in skipped["plan"]["blocks"]}
    assert statuses[first_block["id"]] == "done"
    assert statuses[next_block["id"]] == "skipped"


def test_energy_checkin_changes_suggested_mode(client):
    _clear_day("2026-07-17")
    client.post("/api/day-planner/checkin", json={"date": "2026-07-17", "energy_level": "baixa"})

    payload = client.post("/api/day-planner/generate", json={"date": "2026-07-17"}).get_json()

    assert payload["context"]["energy_level"] == "baixa"
    assert payload["plan"]["plan"]["mode"] == "light"


def test_day_planner_today_api_returns_plan(client):
    _clear_day("2026-07-18")
    client.post("/api/day-planner/generate", json={"date": "2026-07-18", "energy_level": "media"})

    response = client.get("/api/day-planner/today?date=2026-07-18")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["plan"]["plan"]["date"] == "2026-07-18"
    assert payload["next_step"]["microsteps"]


def _clear_day(date_value: str) -> None:
    with get_connection() as conn:
        plan = conn.execute("SELECT id FROM daily_plans WHERE date = ?", (date_value,)).fetchone()
        if plan:
            conn.execute("DELETE FROM daily_plan_blocks WHERE plan_id = ?", (plan["id"],))
            conn.execute("DELETE FROM daily_plans WHERE id = ?", (plan["id"],))
        for table in (
            "daily_energy_checkins",
            "health_import_records",
            "health_sleep_daily",
            "health_steps_daily",
            "health_activities",
            "health_heart_rate_daily",
            "health_data",
            "monitoring_app_usage_daily",
            "daily_records",
        ):
            conn.execute(f"DELETE FROM {table} WHERE date = ?", (date_value,))

