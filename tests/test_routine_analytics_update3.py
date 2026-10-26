from __future__ import annotations

from backend.database import get_connection
from core.tools.health_importer.health_repository import save_activity_records, save_sleep_records, save_steps_records
from core.tools.health_importer.health_schemas import ActivityRecord, SleepStageRecord, StepsRecord
from core.tools.monitoring.monitoring_repository import add_usage_seconds


def test_routine_analytics_combines_health_pc_and_daily_data(client):
    _clear_dates("2026-06-25", "2026-07-01")
    _seed_day(client, "2026-07-01", workout_done=True, sleep_hours=7.5, steps=7000, score_note="bom")
    save_sleep_records([SleepStageRecord("2026-07-01", "00:30:00", 8 * 3600, "light", "sleep.csv")])
    save_steps_records([StepsRecord("2026-07-01", "12:00:00", 8200, "steps.csv")])
    save_activity_records([ActivityRecord("2026-07-01", "17:00:00", "treino", "Treino", 3600, 3000, 0, "activity.csv")])
    add_usage_seconds("VS Code", "Projeto", 7200, "2026-07-01")
    add_usage_seconds("Discord", "Risco", 900, "2026-07-01")

    payload = client.get("/api/routine-analytics?period=7&date=2026-07-01").get_json()
    today = payload["daily"][0]

    assert payload["period_days"] == 7
    assert today["date"] == "2026-07-01"
    assert today["sleep_hours"] == 8
    assert today["steps"] == 8200
    assert today["trained"] is True
    assert today["productive_minutes"] == 120
    assert today["risk_minutes"] == 15
    assert today["focus_good"] is True


def test_routine_analytics_periods_and_empty_days_do_not_break(client):
    response = client.get("/api/routine-analytics?period=30&date=2026-07-01")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["period_days"] == 30
    assert len(payload["daily"]) == 30
    assert payload["daily"][0]["date"] == "2026-07-01"
    assert payload["daily"][-1]["date"] == "2026-06-02"
    assert "safety_note" in payload


def test_routine_analytics_builds_rule_based_insights(client):
    _clear_dates("2026-06-25", "2026-07-01")
    for index, day in enumerate(["2026-06-29", "2026-06-30", "2026-07-01"]):
        _seed_day(client, day, workout_done=True, sleep_hours=8, steps=7000 + index, score_note="treino")
        save_sleep_records([SleepStageRecord(day, "00:00:00", 8 * 3600, "light", "sleep.csv")])
        save_activity_records([ActivityRecord(day, "18:00:00", "treino", "Treino", 3600, 3600, 0, "activity.csv")])
        add_usage_seconds("VS Code", "Projeto", 7200, day)

    payload = client.get("/api/routine-analytics?period=7&date=2026-07-01").get_json()

    assert payload["summary"]["combined_good_days"] >= 3
    assert any("Dias combinados bons" == insight["title"] for insight in payload["insights"])
    assert all("diagnostico" not in insight["message"].lower() for insight in payload["insights"])


def test_routine_analytics_service_accepts_only_supported_periods(client):
    payload = client.get("/api/routine-analytics?period=99&date=2026-07-01").get_json()

    assert payload["period_days"] == 7


def test_routine_analytics_page_loads(client):
    response = client.get("/analytics")

    assert response.status_code == 200
    assert b"Correlacoes" in response.data


def _seed_day(client, date_value: str, *, workout_done: bool, sleep_hours: float, steps: int, score_note: str):
    response = client.post(
        "/api/daily",
        json={
            "date": date_value,
            "workout_done": workout_done,
            "workout_hours": 1 if workout_done else 0,
            "study_done": True,
            "study_hours": 1,
            "programming_done": True,
            "programming_hours": 1,
            "reading_done": False,
            "reading_hours": 0,
            "sleep_hours": sleep_hours,
            "steps": steps,
            "energy": 4,
            "mood": 4,
            "observation": f"analytics {score_note}",
        },
    )
    assert response.status_code == 200


def _clear_dates(start_date: str, end_date: str) -> None:
    with get_connection() as conn:
        for table in (
            "daily_records",
            "health_import_records",
            "health_sleep_daily",
            "health_steps_daily",
            "health_activities",
            "health_heart_rate_daily",
            "health_data",
            "monitoring_app_usage_daily",
        ):
            conn.execute(f"DELETE FROM {table} WHERE date >= ? AND date <= ?", (start_date, end_date))
