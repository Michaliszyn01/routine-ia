from __future__ import annotations

from backend.database import get_connection
from core.tools.focus_mode.focus_repository import ensure_focus_schema
from core.tools.focus_mode.focus_service import record_focus_app_sample


def test_start_focus_from_plan_block_and_complete_marks_block_done(client):
    _clear_update5()
    plan = client.post("/api/day-planner/generate", json={"date": "2026-07-20", "energy_level": "media"}).get_json()
    block = plan["next_step"]

    started = client.post("/api/focus/start", json={"plan_block_id": block["id"]}).get_json()
    session = started["session"]
    completed = client.post("/api/focus/complete", json={"session_id": session["id"]}).get_json()
    fresh = client.get("/api/day-planner/today?date=2026-07-20").get_json()

    assert started["ok"] is True
    assert session["plan_block_id"] == block["id"]
    assert completed["session"]["status"] == "completed"
    assert _block_status(fresh, block["id"]) == "done"


def test_start_quick_focus_pause_resume_and_abandon_keeps_block_available(client):
    _clear_update5()
    quick = client.post("/api/focus/start", json={"title": "Leitura curta", "focus_type": "reading", "planned_minutes": 10}).get_json()["session"]

    paused = client.post("/api/focus/pause", json={"session_id": quick["id"]}).get_json()["session"]
    resumed = client.post("/api/focus/resume", json={"session_id": quick["id"]}).get_json()["session"]
    abandoned = client.post("/api/focus/abandon", json={"session_id": quick["id"], "block_status": "pending"}).get_json()["session"]

    assert quick["plan_block_id"] is None
    assert paused["status"] == "paused"
    assert resumed["status"] == "active"
    assert abandoned["status"] == "abandoned"


def test_app_match_and_mismatch_update_focus_totals(client):
    _clear_update5()
    session = client.post("/api/focus/start", json={"title": "Projeto", "focus_type": "project", "planned_minutes": 25}).get_json()["session"]

    record_focus_app_sample(session["id"], "VS Code", 60)
    updated = record_focus_app_sample(session["id"], "Steam", 30)

    assert updated["focused_seconds"] == 60
    assert updated["distracted_seconds"] == 30


def test_abandon_plan_block_does_not_delete_it(client):
    _clear_update5()
    plan = client.post("/api/day-planner/generate", json={"date": "2026-07-21", "energy_level": "media"}).get_json()
    block = plan["next_step"]
    session = client.post("/api/focus/start", json={"plan_block_id": block["id"]}).get_json()["session"]

    client.post("/api/focus/abandon", json={"session_id": session["id"], "block_status": "pending"})
    fresh = client.get("/api/day-planner/today?date=2026-07-21").get_json()

    assert any(item["id"] == block["id"] for item in fresh["plan"]["blocks"])
    assert _block_status(fresh, block["id"]) == "pending"


def test_does_not_create_two_active_focus_sessions(client):
    _clear_update5()
    first = client.post("/api/focus/start", json={"title": "Primeira", "focus_type": "study"}).get_json()
    second = client.post("/api/focus/start", json={"title": "Segunda", "focus_type": "study"})

    assert first["session"]["status"] == "active"
    assert second.status_code == 400


def test_weekly_review_with_complete_data_returns_json(client):
    _clear_update5()
    client.post("/api/day-planner/generate", json={"date": "2026-07-20", "energy_level": "media"})
    session = client.post("/api/focus/start", json={"date": "2026-07-20", "title": "Projeto Routine IA", "focus_type": "project", "planned_minutes": 50}).get_json()["session"]
    record_focus_app_sample(session["id"], "VS Code", 1800)
    record_focus_app_sample(session["id"], "Discord", 300)
    client.post("/api/focus/complete", json={"session_id": session["id"]})
    _insert_daily("2026-07-20", 80, 7.5)
    _insert_health("2026-07-20")

    response = client.get("/api/weekly-review/range?start=2026-07-20&end=2026-07-26")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["summary"]["average_score"] == 80
    assert payload["focus_summary"]["focused_seconds"] == 1800
    assert payload["top_focus_breakers"][0]["app_name"] == "Discord"
    assert payload["health_summary"]["workouts_done"] >= 1


def test_weekly_review_with_missing_data_is_friendly(client):
    _clear_update5()

    payload = client.get("/api/weekly-review/range?start=2026-08-01&end=2026-08-07").get_json()

    assert payload["summary"]["average_score"] == 0
    assert payload["enough_data"] is False
    assert "poucos dados" in payload["message"]


def test_weekly_review_best_hard_plan_rate_and_language(client):
    _clear_update5()
    _insert_daily("2026-07-22", 90, 8)
    _insert_daily("2026-07-23", 35, 5)
    plan = client.post("/api/day-planner/generate", json={"date": "2026-07-22", "energy_level": "media"}).get_json()
    client.post("/api/day-planner/block/complete", json={"block_id": plan["next_step"]["id"]})

    payload = client.get("/api/weekly-review/range?start=2026-07-20&end=2026-07-26").get_json()
    text = " ".join(payload["insights"] + payload["suggestions"]).lower()

    assert payload["best_day"]["date"] == "2026-07-22"
    assert payload["hard_day"]["date"] == "2026-07-23"
    assert payload["plan_summary"]["completion_rate"] > 0
    assert "falhou" not in text
    assert "desperdicou" not in text


def _clear_update5() -> None:
    ensure_focus_schema()
    with get_connection() as conn:
        for table in ("focus_session_events", "focus_app_usage", "focus_sessions"):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM daily_plan_blocks")
        conn.execute("DELETE FROM daily_plans")
        for table in (
            "daily_records",
            "health_sleep_daily",
            "health_steps_daily",
            "health_activities",
            "health_heart_rate_daily",
            "health_data",
            "monitoring_app_usage_daily",
        ):
            conn.execute(f"DELETE FROM {table}")


def _block_status(payload: dict, block_id: int) -> str:
    return next(item["status"] for item in payload["plan"]["blocks"] if item["id"] == block_id)


def _insert_daily(date_value: str, score: float, sleep_hours: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO daily_records (date, weekday, daily_score, sleep_hours, energy, mood)
            VALUES (?, 'Segunda', ?, ?, 4, 4)
            ON CONFLICT(date) DO UPDATE SET daily_score = excluded.daily_score, sleep_hours = excluded.sleep_hours
            """,
            (date_value, score, sleep_hours),
        )


def _insert_health(date_value: str) -> None:
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO health_sleep_daily (date, total_sleep_seconds) VALUES (?, ?)", (date_value, 8 * 3600))
        conn.execute("INSERT OR REPLACE INTO health_steps_daily (date, total_steps) VALUES (?, ?)", (date_value, 9000))
        conn.execute(
            """
            INSERT OR IGNORE INTO health_activities (date, activity_type, activity_name, elapsed_seconds, active_seconds)
            VALUES (?, 'workout', 'Treino', 3600, 3300)
            """,
            (date_value,),
        )
