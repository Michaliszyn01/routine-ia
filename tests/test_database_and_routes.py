from datetime import date


def test_daily_record_roundtrip_and_dashboard(client):
    payload = {
        "date": date.today().isoformat(),
        "workout_done": True,
        "workout_hours": 1,
        "study_done": True,
        "study_hours": 1,
        "programming_done": True,
        "programming_hours": 1,
        "reading_done": False,
        "reading_hours": 0,
        "sleep_hours": 8,
        "steps": 3500,
        "energy": 4,
        "mood": 4,
        "observation": "pytest smoke",
    }

    save_response = client.post("/api/daily", json=payload)
    assert save_response.status_code == 200
    saved = save_response.get_json()["record"]
    assert saved["date"] == payload["date"]
    assert saved["daily_score"] > 0

    get_response = client.get(f"/api/daily?date={payload['date']}")
    assert get_response.status_code == 200
    assert get_response.get_json()["exists"] is True

    dashboard_response = client.get("/api/dashboard")
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.get_json()
    assert "summary" in dashboard
    assert "charts" in dashboard


def test_today_bundle_smoke(client):
    response = client.get("/api/today")

    assert response.status_code == 200
    body = response.get_json()
    assert "date" in body
    assert "weekday" in body
    assert "editing" in body
