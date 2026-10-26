from core.tools.monitoring.app_rules import normalize_category
from backend.reports import generate_weekly_report
from backend.scoring import calculate_daily_score


def test_calculate_daily_score_caps_at_100():
    record = {
        "workout_done": 1,
        "workout_hours": 10,
        "study_done": 1,
        "study_hours": 10,
        "programming_done": 1,
        "programming_hours": 10,
        "reading_done": 1,
        "reading_hours": 10,
        "sleep_hours": 8,
    }
    goals = {
        "workout": {"active": 1, "daily_hours_goal": 1, "daily_weight": 30},
        "study": {"active": 1, "daily_hours_goal": 1, "daily_weight": 30},
        "programming": {"active": 1, "daily_hours_goal": 1, "daily_weight": 30},
        "reading": {"active": 1, "daily_hours_goal": 1, "daily_weight": 30},
        "sleep": {"active": 1, "daily_weight": 30},
    }

    assert calculate_daily_score(record, goals) == 100


def test_report_generation_shape(client):
    response = client.get("/api/reports/weekly")
    assert response.status_code == 200

    report = response.get_json()
    assert report["engine"].startswith("rules-")
    assert "metrics" in report
    assert isinstance(report["insights"], list)


def test_direct_report_function_shape():
    report = generate_weekly_report("2026-06-22", "2026-06-28")

    assert report["period"]["week_start"] == "2026-06-22"
    assert "metrics" in report
    assert "report_text" in report


def test_app_usage_category_normalizes_accents_and_aliases():
    assert normalize_category("Programacao") == "programacao"
    assert normalize_category("programação") == "programacao"
    assert normalize_category("desconhecido") == "outro"
