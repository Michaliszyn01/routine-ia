from backend.adhd_support import (
    cant_start,
    get_bad_day_presets,
    get_next_action_context,
    recommend_focus,
    save_minimum_day,
    start_bad_day,
)
from backend.checklists import list_checklists, log_checklist
from backend.microtasks import generate_microtasks, list_microtasks, toggle_microtask


def test_next_action_low_energy(client):
    client.post(
        "/api/daily",
        json={"date": "2026-06-30", "energy": 2, "mood": 3, "sleep_hours": 8},
    )

    context = get_next_action_context("2026-06-30")

    assert context["mode"] == "low_energy"
    assert context["energy_band"] == "low"
    assert context["estimated_minutes"] <= 10


def test_next_action_without_study(client):
    client.post(
        "/api/daily",
        json={"date": "2026-07-01", "energy": 4, "mood": 4, "sleep_hours": 8, "study_done": 0},
    )

    context = get_next_action_context("2026-07-01")

    assert context["primary_action"]["category"] in {"estudo", "programacao"}
    assert context["microsteps"]


def test_next_action_bad_day_active(client):
    start_bad_day({"date": "2026-07-02", "preset": "travado"})

    context = get_next_action_context("2026-07-02")

    assert context["mode"] == "bad_day"
    assert context["primary_action"]["source"] == "minimum"


def test_microtasks_generate_and_toggle(client):
    generated = generate_microtasks(
        {"date": "2026-07-03", "title": "Estudar matematica", "category": "estudo"}
    )
    task = generated["microtasks"][0]
    toggled = toggle_microtask({"id": task["id"], "completed": True})
    listed = list_microtasks("2026-07-03")

    assert len(generated["microtasks"]) <= 5
    assert toggled["microtask"]["completed"] == 1
    assert listed["completed"] == 1


def test_bad_day_presets_and_start(client):
    presets = get_bad_day_presets()
    result = start_bad_day({"date": "2026-07-04", "preset": "sem_energia"})

    assert any(item["key"] == "sem_energia" for item in presets["presets"])
    assert result["preset"] == "sem_energia"
    assert result["actions"]


def test_save_minimum_day(client):
    result = save_minimum_day(
        {"date": "2026-07-05", "energy": 2, "mood": 3, "sleep_hours": 6.5, "note": "dia pesado"}
    )

    assert result["success"] is True
    assert result["streak_preserved"] is True
    assert result["minimum_save"]["energy"] == 2


def test_focus_recommendation(client):
    client.post(
        "/api/daily",
        json={"date": "2026-07-06", "energy": 1, "mood": 2, "sleep_hours": 6},
    )

    recommendation = recommend_focus("2026-07-06")

    assert recommendation["recommended_minutes"] <= 10
    assert recommendation["break_minutes"] >= 0


def test_checklists_contextual_and_log(client):
    data = list_checklists("2026-07-07", "programacao")
    suggested = data["suggested"]
    log = log_checklist(
        {
            "date": "2026-07-07",
            "template_id": suggested["id"],
            "completed_items": [suggested["items"][0]["id"]],
        }
    )

    assert suggested["category"] == "programacao"
    assert log["log"]["template_id"] == suggested["id"]


def test_cant_start(client):
    result = cant_start({"energy_level": "baixa", "desired_area": "estudar", "available_minutes": 5})

    assert result["duration"] == 5
    assert result["start_focus_available"] is True
    assert result["microsteps"]


def test_phase2_routes_json(client):
    routes = [
        "/api/adhd/command-center?date=2026-07-08",
        "/api/microtasks?date=2026-07-08",
        "/api/checklists?date=2026-07-08&context=estudo",
        "/api/focus/recommend?date=2026-07-08",
        "/api/bad-day/presets",
    ]

    for route in routes:
        response = client.get(route)
        assert response.status_code == 200
        assert response.is_json
