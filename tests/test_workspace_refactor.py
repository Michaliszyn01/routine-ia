from datetime import date, timedelta


def test_database_engine_and_workspace_routes(client):
    database = client.get("/api/system/database")
    assert database.status_code == 200
    diagnostics = database.get_json()["database"]
    assert diagnostics["integrity"] == "ok"
    assert diagnostics["journal_mode"] == "wal"
    assert diagnostics["foreign_keys"] is True
    assert diagnostics["schema_version"] >= 1

    workspace = client.get(f"/api/workspace?date={date.today().isoformat()}")
    assert workspace.status_code == 200
    body = workspace.get_json()
    assert {"planner", "tasks", "studies", "habits", "focus", "load_balance"} <= set(body)


def test_task_lifecycle(client):
    today = date.today().isoformat()
    created = client.post(
        "/api/tasks",
        json={
            "title": "Revisar funcoes",
            "area": "estudos",
            "priority": 3,
            "scheduled_for": today,
            "estimated_minutes": 30,
        },
    )
    assert created.status_code == 201
    task = created.get_json()["task"]
    assert task["area"] == "estudos"

    listed = client.get(f"/api/tasks?date={today}").get_json()["tasks"]
    assert any(item["id"] == task["id"] for item in listed)

    completed = client.post(f"/api/tasks/{task['id']}/complete", json={"completed": True})
    assert completed.status_code == 200
    assert completed.get_json()["task"]["status"] == "completed"

    archived = client.delete(f"/api/tasks/{task['id']}")
    assert archived.status_code == 200
    assert archived.get_json()["task"]["status"] == "archived"


def test_study_error_creates_spaced_review(client):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    created = client.post(
        "/api/studies/errors",
        json={
            "date": yesterday,
            "subject": "Matematica",
            "topic": "Funcoes",
            "error_type": "calculo",
            "description": "Errou o sinal.",
            "correction": "Revisar a troca de sinal.",
        },
    )
    assert created.status_code == 200
    error_id = created.get_json()["error_record"]["id"]

    due = client.get(f"/api/studies/reviews?date={date.today().isoformat()}").get_json()["reviews"]
    assert any(item["study_error_id"] == error_id for item in due)

    reviewed = client.post(
        f"/api/studies/reviews/{error_id}",
        json={"quality": 4, "date": date.today().isoformat()},
    )
    assert reviewed.status_code == 200
    assert reviewed.get_json()["review"]["repetitions"] == 1
